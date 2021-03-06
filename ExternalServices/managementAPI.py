import sys
import os
import io
sys.path.append("../")
import json
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
from Database.log import DBLog
from WorkflowManager.manager import workflow
from pony.orm.serialization import to_dict
from flask import Flask, request, jsonify, send_file, Response
import base64
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, fresh_jwt_required, get_jwt_identity, set_access_cookies, unset_jwt_cookies
from ExternalDataInterface.client import getEDIHealth, getAllEDIEndpoints, removeEndpoint, ExternalDataInterfaceException
from MachineStatusManager.client import retrieveMachineStatuses, addNewMachine, MachineStatusManagerException, deleteMachine, enableMachine, disableMachine, enableTestModeOnMachine, disableTestModeOnMachine, getMSMHealth
from DataManager.client import getInfoForDataInDM, DataManagerException, getDMHealth, deleteDataViaDM, getByteDataViaDM
from SimulationManager.client import refreshSimilation, SimulationManagerException, cancelSimulation, getSMHealth

logger = log.VestecLogger("Website")

VERSION_PRECLUDE="1.3"
version_number=VERSION_PRECLUDE+"."+VERSION_POSTFIX

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
        logger.Log("Account created for user %s" % username, user=username)

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

    logger.Log(str(request), user=username)

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
    return jsonify({"status": 200, "workflows": json.dumps(allowed_workflows)})

@pny.db_session
def createIncident(username):
    incident_request = request.json    
    incident_name=incident_request.get("name", None)
    incident_kind=incident_request.get("kind", None)
    incident_upper_left_latlong=incident_request.get("upperLeftLatlong", "")
    incident_lower_right_latlong=incident_request.get("lowerRightLatlong", "")
    incident_duration=incident_request.get("duration", None)

    try:
        if incident_duration is not None:
            incident_duration=int(incident_duration)
    except ValueError:
        return jsonify({"status": 400, "msg": "If incident duration is provided then it must be an integer"}), 400

    if RegisteredWorkflow.get(kind=incident_kind) is None:
        return jsonify({"status": 400, "msg": "Incident kind is unknown, this must match a registered workflow that you have permission to access"}), 400
    else:        
        if logins.can_user_access_workflow(username, incident_kind):
            if incident_name and incident_kind:
                incident_id = incidents.createIncident(incident_name, incident_kind, username, incident_upper_left_latlong, incident_lower_right_latlong, incident_duration)
                logger.Log(("Creation of incident kind %s of name %s by %s" % (incident_name, incident_kind, username)), user=username, incidentId=incident_id)
                return jsonify({"status": 201, "msg": "Incident successfully created.", "incidentid" : incident_id}), 201
            else:
                return jsonify({"status": 400, "msg": "Incident name or type is missing"}), 400
        else:
            return jsonify({"msg": "Permission denied to access the workflow kind that this incident is created with, you will need this added for your user"})

def getAllMyIncidents(username, pending_filter, active_filter, completed_filter, cancelled_filter, error_filter, archived_filter):
    incident_summaries=incidents.retrieveMyIncidentSummary(username, pending_filter, active_filter, completed_filter, cancelled_filter, error_filter, archived_filter)
    return jsonify({"status": 200, "incidents": json.dumps(incident_summaries)})

def getIncidentLogs(incident_uuid, username):
    incident_logs=incidents.retrieveIncidentLogs(incident_uuid, username)
    
    if (incident_logs is None):    
        return jsonify({"status": 401, "msg": "Error retrieving incident log"})
    else:
        return jsonify({"status": 200, "incidentId": incident_uuid, "logs": json.dumps(incident_logs)})


def getSpecificIncident(incident_uuid, username):
    incident_info=incidents.retrieveIncident(incident_uuid, username)

    if (incident_info is None):
        logger.Log("User %s raised error retrieving incident %s" % (username, incident_uuid), user=username, incidentId=incident_uuid, type=log.LogType.Error)
        return jsonify({"status": 401, "msg": "Error retrieving incident."})
    else:
        return jsonify({"status": 200, "incident": json.dumps(incident_info)})

def cancelSpecificIncident(incident_uuid, username):
    incidents.cancelIncident(incident_uuid, username)
    return jsonify({"status": 200, "msg": "Incident cancelled"})

def archiveIncident(incident_uuid, username):    
    retval=incidents.archiveIncident(incident_uuid, username)    

    if (retval):
        logger.Log("User %s archived incident %s" % (username, incident_uuid), user=username, incidentId=incident_uuid)
        return jsonify({"status": 200, "msg": "Incident archived"})         
    else:
        logger.Log("User %s raised error archived incident %s" % (username, incident_uuid), user=username, incidentId=incident_uuid, type=log.LogType.Error)
        return jsonify({"status": 401, "msg": "Error archiving incident."})

def activateIncident(incident_uuid, username):
    retval=incidents.activateIncident(incident_uuid, username)    

    if (retval):
        logger.Log("User %s activated incident %s" % (username, incident_uuid), user=username, incidentId=incident_uuid)
        return jsonify({"status": 200, "msg": "Incident activated"})         
    else:
        logger.Log("User %s raised error activating incident %s" % (username, incident_uuid), user=username, incidentId=incident_uuid, type=log.LogType.Error)
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
    try:
        file_info=getInfoForDataInDM(data_uuid)
        byte_data=getByteDataViaDM(data_uuid, gather_metrics=True)
        return send_file(io.BytesIO(byte_data),
                     attachment_filename=file_info["filename"],
                     mimetype=file_info["type"])
    except DataManagerException as err:
        return jsonify({"status" : err.status_code, "msg" : err.message}), err.status_code    

@pny.db_session
def deleteData(data_uuid, incident_uuid, username):
    success=incidents.removeDataFromIncident(data_uuid, incident_uuid, username)
    if success:
        try:
            deleteDataViaDM(data_uuid)        
            return jsonify({"status": 200, "msg": "Data deleted"})
        except DataManagerException as err:
            return jsonify({"status" : err.status_code, "msg" : err.message}), err.status_code
    else:
        return jsonify({"status" : 401, "msg": "Data deletion failed, no incident data set that you can edit"}), 401

@pny.db_session
def performRefreshSimulation(request_json):       
    sim_uuid=request_json.get("sim_uuid", None)
    try:
        refreshSimilation(sim_uuid)
        sim = Simulation[sim_uuid]
        packagedSim=incidents.packageSimulation(sim)
        return jsonify({"status" : 200, "simulation": json.dumps(packagedSim)}), 200
    except SimulationManagerException as err:
        return jsonify({"status" : err.status_code, "msg" : err.message}), err.status_code
 
@pny.db_session
def performCancelSimulation(sim_uuid, username):
    try:
        cancelSimulation(sim_uuid)
        return "Similation cancelled successfully", 200
    except SimulationManagerException as err:
        return jsonify({"status" : err.status_code, "msg" : err.message}), err.status_code
    
@pny.db_session
def getLogs():
    logs = []
    log_records = pny.select(l for l in DBLog)[:]

    for l in log_records:
        lg = {}
        lg["timestamp"] = str(l.timestamp)
        lg["originator"] = l.originator
        lg["user"] = l.user
        lg["type"] = l.type.name
        lg["comment"] = l.comment

        logs.append(lg)

    logs.reverse()
    return jsonify({"status": 200, "logs": json.dumps(logs)})

def getComponentHealths():
    component_healths=[]    
    component_healths.append({"name" : "External data interface", "status" : getEDIHealth()})    
    component_healths.append({"name" : "Simulation manager", "status" : getSMHealth()})
    component_healths.append({"name" : "Machine status manager", "status" : getMSMHealth()})
    component_healths.append({"name" : "Data manager", "status" : getDMHealth()})

    workflowLogs = pny.select(specific_log for specific_log in DBLog if specific_log.originator == "Test workflow")[:]
    if (len(workflowLogs) > 0):
        most_recent=workflowLogs[-1]
        component_healths.append({"name" : "Workflow manager", "status" : most_recent.timestamp.strftime("%H:%M:%S, %d/%m/%Y")})
    else:
        component_healths.append({"name" : "Workflow manager", "status" : "Never"})
    return jsonify({"status": 200, "health": json.dumps(component_healths)})

def updateWorkflowHealthStatus():
    workflow.OpenConnection()
    msg = {}
    msg["IncidentID"]="test_workflow_health"
    workflow.send(message=msg, queue="workflow_running_test")
    workflow.FlushMessages()
    workflow.CloseConnection()
    return jsonify({"status": 200})

def getEDIInfo():    
    return jsonify({"status": 200, "handlers": getAllEDIEndpoints()})

def deleteEDIHandler(retrieved_data): 
    incidentid = retrieved_data.get("incidentid", None)
    endpoint = retrieved_data.get("endpoint", None)
    queuename = retrieved_data.get("queuename", None)
    pollperiod = retrieved_data.get("pollperiod", None)   
    try:
        removeEndpoint(incidentid, endpoint, queuename, pollperiod)
        return jsonify({"status" : 200, "msg": "Handler removed"}), 200
    except ExternalDataInterfaceException as err:
        return jsonify({"status" : err.status_code, "msg": err.message}), err.status_code        

def performRetrieveMachineStatuses():
    return jsonify({"status": 200, "machine_statuses": retrieveMachineStatuses()})

def performAddNewMachine(retrieved_data):
    machine_name=retrieved_data.get("machine_name", None)
    host_name=retrieved_data.get("host_name", None)
    scheduler=retrieved_data.get("scheduler", None)
    connection_type=retrieved_data.get("connection_type", None)
    num_nodes=retrieved_data.get("num_nodes", None)
    cores_per_node=retrieved_data.get("cores_per_node", None)
    base_work_dir=retrieved_data.get("base_work_dir", None)

    try:
        addNewMachine(machine_name, host_name, scheduler, connection_type, num_nodes, cores_per_node, base_work_dir)
        return jsonify({"status" : 200, "msg": "Machine added"}), 200
    except MachineStatusManagerException as err:
        return jsonify({"status" : err.status_code, "msg": err.message}), err.status_code

def performDeleteMachine(machine_id):
    try:
        deleteMachine(machine_id)
        return jsonify({"status" : 200, "msg": "Machine deleted"}), 200
    except MachineStatusManagerException as err:
        return jsonify({"status" : err.status_code, "msg": err.message}), err.status_code

def performEnableMachine(machine_id):
    try:
        enableMachine(machine_id)
        return jsonify({"status" : 200, "msg": "Machine enabled"}), 200
    except MachineStatusManagerException as err:
        return jsonify({"status" : err.status_code, "msg": err.message}), err.status_code

def performDisableMachine(machine_id):
    try:
        disableMachine(machine_id)
        return jsonify({"status" : 200, "msg": "Machine disabled"}), 200
    except MachineStatusManagerException as err:
        return jsonify({"status" : err.status_code, "msg": err.message}), err.status_code

def enableTestModeMachine(machine_id):
    try:
        enableTestModeOnMachine(machine_id)
        return jsonify({"status" : 200, "msg": "Test mode enabled"}), 200
    except MachineStatusManagerException as err:
        return jsonify({"status" : err.status_code, "msg": err.message}), err.status_code

def disableTestModeMachine(machine_id):
    try:
        disableTestModeOnMachine(machine_id)
        return jsonify({"status" : 200, "msg": "Test mode disabled"}), 200
    except MachineStatusManagerException as err:
        return jsonify({"status" : err.status_code, "msg": err.message}), err.status_code

@pny.db_session
def deleteWorkflow(retrieved_data):
    workflow_kind = retrieved_data.get("kind", None)
    registeredworkflows=RegisteredWorkflow.select(lambda wf: wf.kind == workflow_kind)
    if (len(registeredworkflows) >= 1):
        # If there is more than one matching then just grab the first one
        list(registeredworkflows)[0].delete()
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
        specific_workflow_info["shutdownqueuename"]=workflow.shutdown_queue_name
        workflow_info.append(specific_workflow_info)
    return jsonify({"status": 200, "workflows": json.dumps(workflow_info)})

@pny.db_session
def addWorkflow(retrieved_data):    
    workflow_kind = retrieved_data.get("kind", None)
    init_queue_name = retrieved_data.get("initqueuename", None)
    data_queue_name = retrieved_data.get("dataqueuename", None)
    shutdown_queue_name = retrieved_data.get("shutdownqueuename", None)
    istestWorkflow = retrieved_data.get("testworkflow", None)

    registeredworkflows=RegisteredWorkflow.select(lambda wf: wf.kind == workflow_kind)
    if (len(registeredworkflows) == 0):
        # No existing workflow of this kind, all good we will add it
        newwf = RegisteredWorkflow(kind=workflow_kind, init_queue_name=init_queue_name, data_queue_name=data_queue_name, shutdown_queue_name=shutdown_queue_name, test_workflow=istestWorkflow)
        pny.commit()    
        return jsonify({"status": 200, "msg": "Workflow added"})
    else:
        return jsonify({"status": 401, "msg": "Existing workflow of that same kind"}), 401

def getAllUsers():
    return jsonify({"status": 200, "users": json.dumps(logins.get_all_users())})

def getUserDetails(retrieved_data):    
    username=retrieved_data.get("username", None)
    user_details=logins.get_user_details(username)
    return jsonify({"status": 200, "users": json.dumps(user_details)})

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
