import sys
sys.path.append("../")
import requests
import datetime
from flask import Flask, request, jsonify
import Utils.log as log
import json
from apscheduler.schedulers.background import BackgroundScheduler
import pony.orm as pny
from Database import initialiseDatabase
from WorkflowManager import workflow

app = Flask("External Data Interface")
logger = log.VestecLogger("External Data Interface")
push_registered_handlers={}
pull_registered_handlers=[]
poll_scheduler=BackgroundScheduler()

def isHandlerAlreadyRegistered(handlerToAdd, existingList):
    for handler in existingList:
        if handler == handlerToAdd: return True
    return False

class DataHandler:
    def __init__(self, queue_name, incidentID, source_endpoint, pollPeriod=None):
        self.queue_name=queue_name
        self.incidentId=incidentID
        self.source_endpoint=source_endpoint
        self.pollPeriod=pollPeriod
        self.schedulerevent=None
   
    def isPollHandler(self):
        return self.pollPeriod is not None
    def getQueueName(self):
        return self.queue_name
    def getIncidentId(self):
        return self.incidentId
    def getSourceEndpoint(self):
        return self.source_endpoint
    def getPollPeriod(self):
        return self.pollPeriod
    def __eq__(self, other):
        if self.queue_name == other.getQueueName() and self.incidentId == other.getIncidentId() and self.source_endpoint == other.getSourceEndpoint() and self.pollPeriod == other.getPollPeriod():            
            return True
        else:
            return False
    def generateJSON(self):
        return {"queuename": self.queue_name, "endpoint": self.source_endpoint, "incidentid": self.incidentId, "pollperiod": self.pollPeriod}

    def schedule(self):
        self.schedulerevent=poll_scheduler.add_job(self.pollDataSource, 'interval', seconds=self.getPollPeriod())

    def cancel(self):
        if self.schedulerevent is not None:            
            self.schedulerevent.remove()
            self.schedulerevent=None

    def generateDataPacket(self, headers, type):
        data_packet={}
        data_packet["source"]=self.source_endpoint
        data_packet["timestamp"]=int(datetime.datetime.timestamp(datetime.datetime.now()))
        data_packet["headers"]=headers
        data_packet["type"]=type
        data_packet["incidentid"]=self.incidentId
        return data_packet

    def pollDataSource(self):
        x = requests.head(self.source_endpoint, allow_redirects=True)
        if x.ok:
            data_packet=self.generateDataPacket(x.headers, "pull")
            data_packet["status_code"]=x.status_code
            self.sendMessageToWorkflowEngine(data_packet)
            logger.Log(log.LogType.Activity, "Forwarded pulled data from '"+self.source_endpoint+"' to queue '"+self.queue_name+"'")            

    def forwardToQueue(self, data, headers):
        data_packet=self.generateDataPacket(headers, "push")        
        data_packet["payload"]=data.decode('ascii')
        self.sendMessageToWorkflowEngine(data_packet)
        logger.Log(log.LogType.Activity, "Forwarded posted data from '"+self.source_endpoint+"' to queue '"+self.queue_name+"'")           

    def sendMessageToWorkflowEngine(self, data_packet):
        workflow.OpenConnection()
        msg={}
        if self.incidentId is None:
            msg["IncidentID"] =  workflow.CreateIncident(name="test fire", kind="FIRE")
        else:
            msg["IncidentID"] = self.incidentId
        msg["data"]=data_packet
        workflow.send(message=msg, queue=self.queue_name)
        workflow.FlushMessages()
        workflow.CloseConnection()

def handlePostOfData(source, data, headers):    
    if source in push_registered_handlers:  
        logger.Log(log.LogType.Activity, "Data posted from '"+source+"' actioning with atleast one handler that matches")      
        for handler in push_registered_handlers[source]:
            handler.forwardToQueue(data, headers)
        return jsonify({"status": 200, "msg": "Data received"}) 
    else:
        logger.Log(log.LogType.Error, "Data posted from '"+source+"' and ignoring as there are no handlers that match")      
        return jsonify({"status": 400, "msg": "No matching handler registered"})

@app.route("/EDI", methods=["POST"])
def post_data_anon():    
    return handlePostOfData(request.remote_addr, request.get_data(), dict(request.headers))    

@app.route("/EDI/<sourceid>", methods=["POST"])
def post_data(sourceid):
    return handlePostOfData(sourceid, request.get_data(), dict(request.headers))

def generateDataHandler(dict):
    dict = request.get_json()
    queue_name = dict["queuename"]
    incident_ID = dict["incidentid"]
    source_endpoint = dict["endpoint"]
    if "pollperiod" in dict:
        pollperiod = dict["pollperiod"]
    else:
        pollperiod=None
    return DataHandler(queue_name, incident_ID, source_endpoint, pollperiod)

@app.route("/EDImanager/health", methods=["GET"])
def get_health():
    return jsonify({"status": 200})

@app.route("/EDImanager/register", methods=["POST"])
@pny.db_session
def register_handler():
    dict = request.get_json()
    handler=generateDataHandler(dict)
    source_endpoint=handler.getSourceEndpoint()
    if handler.isPollHandler():
        if not isHandlerAlreadyRegistered(handler, pull_registered_handlers):
            pull_registered_handlers.append(handler)
            handler.schedule()
            logger.Log(log.LogType.Activity, "Poll based handler registered for '"+source_endpoint+"' with period "+handler.getPollPeriod()+"s")
            return jsonify({"status": 200, "msg": "Handler registered"})
        else:
            logger.Log(log.LogType.Error, "Attempted to register poll based handler for '"+source_endpoint+"' but already registered")
            return jsonify({"status": 400, "msg": "Handler already registered for polling"})
    else:
        if source_endpoint not in push_registered_handlers:
            push_registered_handlers[source_endpoint]=[]
        if not isHandlerAlreadyRegistered(handler, push_registered_handlers[source_endpoint]):
            push_registered_handlers[source_endpoint].append(handler)
            logger.Log(log.LogType.Activity, "Push based handler registered for '"+source_endpoint+"'")     
            return jsonify({"status": 200, "msg": "Handler registered"})
        else:
            logger.Log(log.LogType.Error, "Attempted to register push based handler for '"+source_endpoint+"' but already registered")
            return jsonify({"status": 400, "msg": "Handler already registered for push"})

@app.route("/EDImanager/remove", methods=["POST"])
@pny.db_session
def remove_handler():
    dict = request.get_json()
    remove_handler=generateDataHandler(dict)
    handler_removed=False
    for handler in pull_registered_handlers:
        if remove_handler == handler:
            pull_registered_handlers.remove(handler)
            handler.cancel()
            handler_removed=True
    source_endpoint=remove_handler.getSourceEndpoint()
    if source_endpoint in push_registered_handlers:        
        for handler in push_registered_handlers[source_endpoint]:
            if (remove_handler == handler):
                push_registered_handlers[source_endpoint].remove(handler)
                handler_removed=True

    if handler_removed:
        logger.Log(log.LogType.Activity, "Handler removed for '"+source_endpoint+"'")
        return jsonify({"status": 200, "msg": "Handler removed"})
    else:
        logger.Log(log.LogType.Error, "No handler found for removal for '"+source_endpoint+"'")
        return jsonify({"status": 400, "msg": "No existing handler registered"})

@app.route("/EDImanager/list/<endpoint>", methods=["GET"])
def list_handlers_withep(endpoint):
    built_up_json_src=[]
    for handler in pull_registered_handlers:
        if handler.getSourceEndpoint==endpoint:
            built_up_json_src.extend(handler.generateJSON())
    if endpoint in push_registered_handlers:
        built_up_json_src.extend(buildDescriptionOfHandlers(push_registered_handlers[endpoint]))
    return json.dumps(built_up_json_src)    

@app.route("/EDImanager/list", methods=["GET"])
def list_handlers():
    built_up_json_src=buildDescriptionOfHandlers(pull_registered_handlers)    
    for value in push_registered_handlers.values():
        built_up_json_src.extend(buildDescriptionOfHandlers(value))
    return json.dumps(built_up_json_src)

def buildDescriptionOfHandlers(handler_list):
    json_to_return=[]
    for handler in handler_list:
        json_to_return.append(handler.generateJSON())
    return json_to_return

if __name__ == "__main__":
    initialiseDatabase()
    poll_scheduler.start()
    app.run(host="0.0.0.0", port=5501)