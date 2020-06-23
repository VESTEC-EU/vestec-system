import sys
import os
import io
sys.path.append("../")
import json
import requests
import pony.orm as pny
import Utils.log as log
import Database
import datetime
from version_info import VERSION_POSTFIX
from uuid import uuid4
from ExternalServices import logins
from ExternalServices import incidents
from Database.users import User
from Database.job import Job
from Database.queues import Queue
from Database.machine import Machine
from Database.activity import Activity
from Database.workflow import RegisteredWorkflow, Simulation
from Database.localdatastorage import LocalDataStorage
from WorkflowManager import workflow
from pony.orm.serialization import to_dict
from flask import Flask, request, jsonify, send_file, Response
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, fresh_jwt_required, get_jwt_identity, set_access_cookies, unset_jwt_cookies

logger = log.VestecLogger("Website")

VERSION_PRECLUDE="1.2"
version_number=VERSION_PRECLUDE+"."+VERSION_POSTFIX

if "VESTEC_SM_URI" in os.environ:
    SM_URL= os.environ["VESTEC_SM_URI"]
else:
    SM_URL = 'http://localhost:5505/SM'

if "VESTEC_EDI_URI" in os.environ:
    EDI_URL = os.environ["VESTEC_EDI_URI"]
else:
    EDI_URL= 'http://localhost:5501/EDImanager'

if "VESTEC_MSM_URI" in os.environ:
    MSM_URL = os.environ["VESTEC_MSM_URI"]
else:
    MSM_URL= 'http://localhost:5502/MSM'

if "VESTEC_DM_URI" in os.environ:
    DATA_MANAGER_URL = os.environ["VESTEC_DM_URI"]
else:
    DATA_MANAGER_URL = 'http://localhost:5000/DM'

def version():
    return jsonify({"status": 200, "version": version_number})

def signup():
    if not request.is_json:
        return jsonify({"msg": "Required JSON not found in request."}), 400

    user = request.json
    username = user.get("username", None)
    name = user.get("name", None)
    email = user.get("email", None)
    password = user.get("password", None)

    user_create = logins.add_user(username, name, email, password)

    if user_create == 1:
        msg = "Account created for user %s" % username
        logger.Log(log.LogType.Logins, msg, user=username)

        return jsonify({"status": 201, "msg": "User succesfully created. Log in."})
    else:
        return jsonify({"status": 409, "msg": "User already exists. Please try again."})

def getUserType(username):
    access_level=logins.get_user_access_level(username)
    return jsonify({"status": 200, "access_level": access_level})

def login():
    if not request.is_json:
        return jsonify({"msg": "Incorrect username or password. Please try again."})

    login = request.json
    username = login.get("username", None)
    password = login.get("password", None)
    authorise = False

    if username and password:
        authorise, message = logins.verify_user(username, password)

    if authorise:
        access_token = create_access_token(identity=username, fresh=True, expires_delta=False)
        response = jsonify({"status": 200, "access_token": access_token})        

        return response
    else:
        return jsonify({"status": 400, "msg": message})

    logger.Log(log.LogType.Website, str(request), user=username)

def changePassword():
    login = request.json
    username = login.get("username", None)
    password = login.get("password", None)
    
    if username and password:
        success=logins.change_user_password(username, password)
        if (success):
            return jsonify({"status": 200, "msg": "Password changed"})
    
    return jsonify({"status": 400, "msg": "Can not change password"})

def getMyWorkflows(username):
    allowed_workflows=logins.get_allowed_workflows(username)
    return json.dumps(allowed_workflows) 

def createIncident(username):
    incident_request = request.json    
    incident_name=incident_request.get("incidentName", None)
    incident_kind=incident_request.get("incidentType", None)
    incident_upper_left_latlong=incident_request.get("upperLeftLatlong", "")
    incident_lower_right_latlong=incident_request.get("lowerRightLatlong", "")
    incident_duration=incident_request.get("duration", None)
    if incident_name and incident_kind:
        job_id = incidents.createIncident(incident_name, incident_kind, username, incident_upper_left_latlong, incident_lower_right_latlong)
        logger.Log(log.LogType.Website, ("Creation of incident kind %s of name %s by %s" % (incident_name, incident_kind, username)), user=username)
        return jsonify({"status": 201, "msg": "Incident successfully created.", "incidentid" : job_id})    
    else:
        return jsonify({"status": 400, "msg": "Incident name or type is missing"})

def getAllMyIncidents(username, pending_filter, active_filter, completed_filter, cancelled_filter, error_filter, archived_filter):
    incident_summaries=incidents.retrieveMyIncidentSummary(username, pending_filter, active_filter, completed_filter, cancelled_filter, error_filter, archived_filter)
    return jsonify({"status": 200, "incidents": json.dumps(incident_summaries)})

def getSpecificIncident(incident_uuid, username):
    incident_info=incidents.retrieveIncident(incident_uuid, username)

    if (incident_info is None):
        logger.Log(log.LogType.Website, "User %s raised error retrieving incident %s" % (username, incident_uuid), user=username)
        return jsonify({"status": 401, "msg": "Error retrieving incident."})
    else:
        return jsonify({"status": 200, "incident": json.dumps(incident_info)})

def cancelSpecificIncident(incident_uuid, username):
    incidents.cancelIncident(incident_uuid, username)
    return jsonify({"status": 200, "msg": "Incident cancelled"})

def archiveIncident(incident_uuid, username):    
    retval=incidents.archiveIncident(incident_uuid, username)    

    if (retval):
        logger.Log(log.LogType.Website, "User %s archived incident %s" % (username, incident_uuid), user=username)
        return jsonify({"status": 200, "msg": "Incident archived"})         
    else:
        logger.Log(log.LogType.Website, "User %s raised error archived incident %s" % (username, incident_uuid), user=username)
        return jsonify({"status": 401, "msg": "Error archiving incident."})

def activateIncident(incident_uuid, username):
    retval=incidents.activateIncident(incident_uuid, username)    

    if (retval):
        logger.Log(log.LogType.Website, "User %s activated incident %s" % (username, incident_uuid), user=username)
        return jsonify({"status": 200, "msg": "Incident activated"})         
    else:
        logger.Log(log.LogType.Website, "User %s raised error activating incident %s" % (username, incident_uuid), user=username)
        return jsonify({"status": 401, "msg": "Error retrieving incident."})

def updateDataMetadata(username):
    incident_request = request.json    
    data_uuid=incident_request.get("data_uuid", None)
    incident_uuid=incident_request.get("incident_uuid", None)
    data_type=incident_request.get("type", None)
    data_comments=incident_request.get("comments", None)
    success=incidents.updateDataMetaData(data_uuid, incident_uuid, data_type, data_comments, username)
    if success:
        return jsonify({"status": 200, "msg": "Metadata updated"})
    else:
        return jsonify({"status": 401, "msg": "Metadata update failed, no incident data-set that you can edit"})       

def getDataSets(data_type, incident_uuid, username):
    datasets=incidents.retrieveMatchingDatasets(data_type, incident_uuid, username)
    if (datasets is None):
        return jsonify({"status": 401, "msg": "Error no matching datasets found"})
    else:
        return jsonify({"status": 200, "datasets": datasets})

def getDataMetadata(data_uuid, incident_uuid, username):
    meta_data=incidents.retrieveDataMetaData(data_uuid, incident_uuid, username)
    if (meta_data is None):
        return jsonify({"status": 401, "msg": "Error can not find matching incident dataset."})
    else:
        return jsonify({"status": 200, "metadata": meta_data}) 

def downloadData(data_uuid):
    data_info=requests.get(DATA_MANAGER_URL+"/info/" + data_uuid)
    file_info=data_info.json()
    if (file_info["storage_technology"]=="VESTECDB" and file_info["machine"]=="localhost"):
        data_dump=LocalDataStorage[file_info["filename"]]
        return send_file(io.BytesIO(data_dump.contents),
                     attachment_filename=data_dump.filename,
                     mimetype=data_dump.filetype)
    return jsonify({"status": 400, "msg" : "Only datasets stored on VESTEC server currently supported"})

@pny.db_session
def deleteData(data_uuid, incident_uuid, username):
    success=incidents.removeDataFromIncident(data_uuid, incident_uuid, username)
    if success:
        data_info=requests.get(DATA_MANAGER_URL+"/info/" + data_uuid)
        file_info=data_info.json()
        requests.delete(DATA_MANAGER_URL+"/remove/" + data_uuid)    
        return jsonify({"status": 200, "msg": "Data deleted"}) 
    else:
        return jsonify({"status": 401, "msg": "Data deletion failed, no incident data set that you can edit"}) 

@pny.db_session
def refreshSimulation(request_json):       
    sim_uuid=request_json.get("sim_uuid", None)
    returned_info = requests.post(SM_URL + '/refresh/'+sim_uuid)
    sim = Simulation[sim_uuid]
    packagedSim=incidents.packageSimulation(sim)
    return jsonify({"status": 200, "simulation": json.dumps(packagedSim)})     

@pny.db_session
def cancelSimulation(sim_uuid, username):
    returned_info = requests.delete(SM_URL + '/simulation/'+sim_uuid)    
    return Response(returned_info.content, returned_info.status_code)

@pny.db_session
def getLogs():
    logs = []
    log_records = pny.select(l for l in log.DBLog)[:]

    for l in log_records:
        lg = {}
        lg["timestamp"] = str(l.timestamp)
        lg["originator"] = l.originator
        lg["user"] = l.user
        lg["type"] = l.type.name
        lg["comment"] = l.comment

        logs.append(lg)

    logs.reverse()
    return json.dumps(logs)

def _getHealthOfComponent(component_name, displayname):
    bd={}
    bd["name"]=displayname
    try:
        edi_health = requests.get(component_name + '/health')        
        if edi_health.status_code == 200:
            bd["status"]=True
        else:
            bd["status"]=False
    except:
        bd["status"]=False
    return bd

def getComponentHealths():
    component_healths=[]    
    component_healths.append(_getHealthOfComponent(EDI_URL, "External data interface"))    
    component_healths.append(_getHealthOfComponent(SM_URL, "Simulation manager"))    
    component_healths.append(_getHealthOfComponent(MSM_URL, "Machine status manager"))    
    component_healths.append(_getHealthOfComponent(DATA_MANAGER_URL, "Data manager"))
    return json.dumps(component_healths)

def getEDIInfo():
    edi_info = requests.get(EDI_URL + '/list')    
    return jsonify({"status": 200, "handlers": edi_info.json()})

def deleteEDIHandler(retrieved_data):    
    deleted_info = requests.post(EDI_URL + '/remove', json=retrieved_data)    
    return Response(deleted_info.content, deleted_info.status_code)

def retrieveMachineStatuses():
    machine_statuses=requests.get(MSM_URL + '/machinestatuses')
    return jsonify({"status": 200, "machine_statuses": machine_statuses.json()})

def addNewMachine(retrieved_data):
    created_info = requests.post(MSM_URL + '/add', json=retrieved_data)    
    return Response(created_info.content, created_info.status_code)

def enableMachine(machine_id):
    enabled_info = requests.post(MSM_URL + '/enable/'+machine_id)    
    return Response(enabled_info.content, enabled_info.status_code)

def disableMachine(machine_id):
    disabled_info = requests.post(MSM_URL + '/disable/'+machine_id)    
    return Response(disabled_info.content, disabled_info.status_code)

def enableTestModeMachine(machine_id):
    enabled_info = requests.post(MSM_URL + '/enable_testmode/'+machine_id)    
    return Response(enabled_info.content, enabled_info.status_code)

def disableTestModeMachine(machine_id):
    disabled_info = requests.post(MSM_URL + '/disable_testmode/'+machine_id)    
    return Response(disabled_info.content, disabled_info.status_code)    

@pny.db_session
def deleteWorkflow(retrieved_data):
    workflow_kind = retrieved_data.get("kind", None)
    item=RegisteredWorkflow.get(kind=workflow_kind)
    item.delete()
    pny.commit()    
    return jsonify({"status": 200, "msg": "Workflow deleted"})

@pny.db_session
def getWorkflowInfo():
    workflow_info=[]    
    registeredworkflows=pny.select(registeredworkflow for registeredworkflow in RegisteredWorkflow)
    for workflow in registeredworkflows:
        specific_workflow_info={}
        specific_workflow_info["kind"]=workflow.kind
        specific_workflow_info["initqueuename"]=workflow.init_queue_name
        specific_workflow_info["dataqueuename"]=workflow.data_queue_name
        workflow_info.append(specific_workflow_info)
    return json.dumps(workflow_info)

@pny.db_session
def addWorkflow(retrieved_data):    
    workflow_kind = retrieved_data.get("kind", None)
    init_queue_name = retrieved_data.get("initqueuename", None)
    data_queue_name = retrieved_data.get("dataqueuename", None)
    istestWorkflow = retrieved_data.get("testworkflow", None)    
    newwf = RegisteredWorkflow(kind=workflow_kind, init_queue_name=init_queue_name, data_queue_name=data_queue_name, test_workflow=istestWorkflow)

    pny.commit()    
    return jsonify({"status": 200, "msg": "Workflow added"})

def getAllUsers():
    return json.dumps(logins.get_all_users())

def getUserDetails(retrieved_data):    
    username=retrieved_data.get("username", None)
    user_details=logins.get_user_details(username)
    return json.dumps(user_details) 

@pny.db_session
def deleteUser(retrieved_data):
    username = retrieved_data.get("username", None)
    stored_user=User.get(username=username)
    if (stored_user is not None):        
        stored_user.delete()
        pny.commit()    
        return jsonify({"status": 200, "msg": "User edited"})
    else:
        return jsonify({"status": 401, "msg": "User deletion failed"})


@pny.db_session
def editUserDetails(retrieved_data):
    username = retrieved_data.get("username", None)
    stored_user=User.get(username=username)
    stored_user.name=retrieved_data.get("name", None)
    stored_user.email=retrieved_data.get("email", None)
    if retrieved_data.get("type", None)=="user":
        stored_user.access_rights=0
    elif retrieved_data.get("type", None)=="administrator":
        stored_user.access_rights=1
    stored_user.enabled=retrieved_data.get("enabled", None)    
    pny.commit()    
    return jsonify({"status": 200, "msg": "User edited"})

@pny.db_session
def addUserToWorkflow(retrieved_data):    
    username = retrieved_data.get("username", None)
    workflow_kind = retrieved_data.get("workflow", None)
    user=User.get(username=username)
    workflow=RegisteredWorkflow.get(kind=workflow_kind)
    user.allowed_workflows.add(workflow)
    pny.commit()    
    return jsonify({"status": 200, "msg": "Workflow added"})

@pny.db_session
def removeUserFromWorkflow(retrieved_data):    
    username = retrieved_data.get("username", None)
    workflow_kind = retrieved_data.get("workflow", None)[0]    
    user=User.get(username=username)    
    for item in user.allowed_workflows:        
        if (item.kind == workflow_kind):            
            user.allowed_workflows.remove(item);
    pny.commit()    
    return jsonify({"status": 200, "msg": "Workflow removed"})