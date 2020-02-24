import sys
sys.path.append("../")
from flask import Flask, request, jsonify
import Utils.log as log
import json
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask("External Data Interface")
logger = log.VestecLogger("External Data Interface")
registered_handlers={}
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
    def pollDataSource(self):
        print("Ping source "+self.source_endpoint)


@app.route("/EDI", methods=["POST"])
def post_data():
    data = request.get_data()
    source_address = request.remote_addr
    if source_address in registered_handlers:
        print("got data from: "+request.remote_addr+" Data: "+str(data))        
        return jsonify({"status": 201, "msg": "Data received"}) 
    else:
        return jsonify({"status": 400, "msg": "No matching handler registered"})

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

@app.route("/EDI/register", methods=["POST"])
def register_handler():
    dict = request.get_json()
    handler=generateDataHandler(dict)
    source_endpoint=handler.getSourceEndpoint()
    if source_endpoint not in registered_handlers:
        registered_handlers[source_endpoint]=[]
    if not isHandlerAlreadyRegistered(handler, registered_handlers[source_endpoint]):
        registered_handlers[source_endpoint].append(handler)
        if handler.isPollHandler():
            handler.schedule()
        return jsonify({"status": 201, "msg": "Handler registered"})
    else:
        return jsonify({"status": 400, "msg": "Handler already registered"})

@app.route("/EDI/remove", methods=["POST"])
def remove_handler():
    dict = request.get_json()
    remove_handler=generateDataHandler(dict)
    source_endpoint=remove_handler.getSourceEndpoint()
    if source_endpoint in registered_handlers:        
        for handler in registered_handlers[source_endpoint]:
            if (remove_handler == handler):
                registered_handlers[source_endpoint].remove(handler)
                handler.cancel()
                return jsonify({"status": 201, "msg": "Handler removed"})
    return jsonify({"status": 400, "msg": "No existing handler registered"})

@app.route("/EDI/list/<endpoint>", methods=["GET"])
def list_handlers_withep(endpoint):
    if endpoint in registered_handlers:
        built_up_json_src=buildDescriptionOfHandlers(registered_handlers[endpoint])
        return json.dumps(built_up_json_src)
    else:
        return json.dumps([])

@app.route("/EDI/list", methods=["GET"])
def list_handlers():
    built_up_json_src=[]
    for value in registered_handlers.values():
        built_up_json_src.extend(buildDescriptionOfHandlers(value))
    return json.dumps(built_up_json_src)

def buildDescriptionOfHandlers(handler_list):
    json_to_return=[]
    for handler in handler_list:
        json_to_return.append(handler.generateJSON())
    return json_to_return

if __name__ == "__main__":
    poll_scheduler.start()
    app.run(host="0.0.0.0", port=5501)