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
from Database.edistorage import EDIHandler
from WorkflowManager import workflow

from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor

app = Flask("External Data Interface")
logger = log.VestecLogger("External Data Interface")

#rabbitMQ is not threadsafe so we only want one worker thread else we get funny crashes
poll_scheduler=BackgroundScheduler(executors={"default": ThreadPoolExecutor(1)})



#schedule a handler. Pass in its EDIHandler id and pollperiod in seconds
def scheduleHandler(id, seconds):
    id = str(id)
    poll_scheduler.add_job(pollDataSource, 'interval',args=[id], seconds=seconds, id = id)
    print("Scheduled pull handler with ID %s"%id)

#cancel a handler. Pass in its EDIHandler id
def cancelScheduledHandler(id):
    id = str(id)
    print("Cancelling scheduled job with ID %s"%id)
    poll_scheduler.remove_job(id)

#This is called by a poll handler (see scheduleHandler above for how it is scheduled)
@pny.db_session
def pollDataSource(id):
    #get the EDIHandler associated with this id
    handler = EDIHandler.get(id = int(id))
    
    #Check to see if the handler's incident is still active. If not, stop this scheduled poll, and delete the hander from the database
    if not workflow._IsActive(handler.incidentid):
        print("Incident no longer active: Cancelling this background handler")
        cancelScheduledHandler(id)
        handler.delete()
        return
    
    #get the header from the endpoint, and send it off to the workflow
    x = requests.head(handler.endpoint, allow_redirects=True)
    if x.ok:
        data_packet=generateDataPacket(x.headers, "pull",handler.endpoint,handler.incidentid)
        data_packet["status_code"]=x.status_code
        print("Got datapacket from '%s'"%handler.endpoint)
        sendMessageToWorkflowEngine(data_packet,handler.queuename,handler.incidentid)
        logger.Log(log.LogType.Activity, "Forwarded pulled data from '"+handler.endpoint+"' to queue '"+handler.queuename+"'")            


#Takes a request header and packages it up into a dict for sending to the workflow
def generateDataPacket(headers, type, endpoint,incidentid):
        data_packet={}
        data_packet["source"]=endpoint
        data_packet["timestamp"]=int(datetime.datetime.timestamp(datetime.datetime.now()))
        #requests outputs a CaseInsensitiveDict which cannot be jsonified so we need do convert this to a regular dict
        data_packet["headers"]=dict(headers) 
        data_packet["type"]=type
        data_packet["incidentid"]=incidentid
        return data_packet



##### NEED TO FIX THIS FOR THREAD SAFTY##############
def sendMessageToWorkflowEngine(data_packet, queue, incidentId):
    workflow.OpenConnection()
    msg={}
    if incidentId is None:
        raise Exception("IncidentID Cannot be None")
    else:
        msg["IncidentID"] = incidentId
    msg["data"]=data_packet
    workflow.send(message=msg, queue=queue)
    workflow.FlushMessages()
    workflow.CloseConnection()


 #Send the data and header to the workflow system
def forwardToQueue(data, headers, endpoint, queue,incidentid):
    data_packet=generateDataPacket(headers, "push",endpoint,incidentid)        
    data_packet["payload"]=data.decode('ascii')
    sendMessageToWorkflowEngine(data_packet, queue,incidentid)
    logger.Log(log.LogType.Activity, "Forwarded posted data from '"+ endpoint +"' to queue '"+queue+"'")


#handles when data is posted (pushed) to the system
@pny.db_session
def handlePostOfData(endpoint, data, headers):    
    handlers = EDIHandler.select(lambda h: h.endpoint==endpoint and h.type == "PUSH")
    if len(handlers) > 0:
        logger.Log(log.LogType.Activity, "Data posted from '"+endpoint+"' actioning with at least one handler that matches") 

        for handler in handlers:
            forwardToQueue(data,headers,endpoint,handler.queuename, handler.incidentid)

        return jsonify({"status": 200, "msg": "Data received"}) 
    else:
        logger.Log(log.LogType.Error, "Data posted from '"+endpoint+"' and ignoring as there are no handlers that match")      
        return jsonify({"status": 400, "msg": "No matching handler registered"})

#if we register a remote host (e.g. www.website.com) as an endpoint and this pushes
#useful for data which is not necessarily incident specific but which should be pushed
#like notification of new weather data which could be of use to many different incidents
@app.route("/EDImanager", methods=["POST"])
def post_data_anon():
    print("anonymous data posted")
    print("posted by ",request.remote_addr)
    print("Data =", request.get_data())
    print("Header=", request.headers)
    return handlePostOfData(request.remote_addr, request.get_data(), dict(request.headers))    

#way to push data to the EDI, giving the endpoint
@app.route("/EDImanager/<sourceid>", methods=["POST"])
def post_data(sourceid):
    print("Data posted to %s"%sourceid)
    print("Data =", request.get_data())
    print("Header=", request.headers)
    return handlePostOfData(sourceid, request.get_data(), dict(request.headers))


@app.route("/EDImanager/health", methods=["GET"])
def get_health():
    return jsonify({"status": 200})

#register a handler
@app.route("/EDImanager/register",methods=["POST"])
@pny.db_session
def register():
    #parse the request header for the info we need
    d = request.get_json()
    try:
        queuename = d["queuename"]
        incidentid = d["incidentid"]
        endpoint = d["endpoint"]
        if "pollperiod" in d:
            pollperiod = d["pollperiod"]
        else:
            pollperiod=None
    except KeyError:
        return jsonify({"status": 400, "msg": "The request header does not contain the required fields"}), 400
    
    #See if this handler already exists. If so, do nothing and return a 400
    handlers = EDIHandler.select(lambda d: d.queuename==queuename
                             and d.incidentid==incidentid 
                             and d.endpoint==endpoint 
                             and d.pollperiod==pollperiod)
    if len(handlers) >0:
        return jsonify({"status":400, "msg": "Handler already registered"}), 400


    if pollperiod is None:
        handlertype = "PUSH"
    else:
        handlertype= "PULL"


    handler = EDIHandler(queuename=queuename,
                        incidentid=incidentid,
                        endpoint=endpoint,
                        type = handlertype,
                        pollperiod=pollperiod)
    #ensure we commit this so we get an ID back for the handler
    pny.commit()

    
    if handlertype=="PUSH":
        logger.Log(log.LogType.Activity, "Push based handler registered for '"+endpoint+"'")     
    
    else:
        scheduleHandler(id = handler.id, seconds = pollperiod)
        logger.Log(log.LogType.Activity, "Poll based handler registered for '"+endpoint+"' with period "+str(pollperiod)+"s")
    
    return jsonify({"status": 200, "msg": "Handler registered"}), 200
        

#Remove a handler
@app.route("/EDImanager/remove", methods=["POST"])
@pny.db_session
def remove():
    #parse the request header for the info we need
    d = request.get_json()
    try:
        queuename = d["queuename"]
        incidentid = d["incidentid"]
        endpoint = d["endpoint"]
        if "pollperiod" in d:
            pollperiod = d["pollperiod"]
        else:
            pollperiod=None
    except KeyError:
        return jsonify({"status": 400, "msg": "The request header does not contain the required fields"}), 400
    
    #get any handlers that match this
    handlers = EDIHandler.select(lambda d: d.queuename==queuename
                            and d.incidentid==incidentid 
                            and d.endpoint==endpoint 
                            and d.pollperiod==pollperiod)
    
    print("endpoint = ", endpoint)
    
    #if there are no such handlers, return an error
    if len(handlers) == 0:
        logger.Log(log.LogType.Error, "No handler found for removal for '"+endpoint+"'")
        return jsonify({"status": 400, "msg": "No existing handler registered"}), 400

    
    #loop through handlers (should just be one...) and delete them
    for handler in handlers:
        if handler.type == "PULL":
            print("REMOVED PULL HANDLER")
            cancelScheduledHandler(handler.id)
        else:
            print("REMOVED PUSH HANDLER")

        handler.delete()

        logger.Log(log.LogType.Activity, "Handler removed for '"+endpoint+"'")

    return jsonify({"status": 200, "msg": "Handler removed"}), 200



#gets info on the requested endpoint
@app.route("/EDImanager/list/<endpoint>", methods=["GET"])
@pny.db_session
def list_handlers_withep(endpoint):
    l=[]
    for handler in EDIHandler.select(lambda h: h.endpoint == endpoint):
        l.append(handler.to_dict(exclude=["id"]))
    return json.dumps(l)

#gets info on all endpoints registered
@app.route("/EDImanager/list", methods=["GET"])
@pny.db_session
def list_handlers(): 
    l=[]
    for handler in EDIHandler.select():
        l.append(handler.to_dict(exclude=["id"]))
    return json.dumps(l)


#reload handlers from the database
@pny.db_session
def reloadEDIStateFromDB():
    handlers=EDIHandler.select()
    numpull = 0
    numpush = 0
    
    #check to see if any of the handlers are for incidents that no longer exist
    todelete=[]
    for handler in handlers:
        if not workflow._IsActive(handler.incidentid):
            todelete.append(handler)

    #delete obsolete handlers
    for handler in todelete:
        handler.delete()
        print('Deleting handler for inactive incident')

    #Now re-create the remaining handlers
    for handler in handlers:
        if handler.type == "PULL":
            scheduleHandler(handler.id,handler.pollperiod)
            numpull +=1
        else:
            numpush +=1

    print("Reinitialised EDI with %d push handlers and %d pull handlers"%(numpush,numpull))


if __name__ == "__main__":
    initialiseDatabase()
    poll_scheduler.start()
    reloadEDIStateFromDB()
    app.run(host="0.0.0.0", port=5501)
    
    print("Closing Thread pool")
    poll_scheduler.shutdown()
