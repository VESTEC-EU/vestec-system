#!/usr/local/bin/flask
'''render_template loads html pages of the application
'''
import sys
import os
sys.path.append("../")
import json
import requests
import pony.orm as pny
import Utils.log as log
import Database
import datetime
from uuid import uuid4
from website import logins
from website import incidents
from Database.users import User
from Database.job import Job
from Database.queues import Queue
from Database.machine import Machine
from Database.activity import Activity
from Database.workflow import RegisteredWorkflow
from WorkflowManager import workflow
from pony.orm.serialization import to_dict
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, fresh_jwt_required, get_jwt_identity, set_access_cookies, unset_jwt_cookies

# Initialise database
Database.initialiseDatabase()

# Initialise services
app = Flask(__name__)  # create an instance if the imported Flask class
logger = log.VestecLogger("Website")

if "VESTEC_MANAGER_URI" in os.environ:
    JOB_MANAGER_URI = os.environ["VESTEC_MANAGER_URI"]
else:
    JOB_MANAGER_URI = 'http://127.0.0.1:5500/jobs'
    EDI_URL= 'http://127.0.0.1:5501/EDImanager'

# Initialise JWT
app.config["JWT_SECRET_KEY"] = os.environ["JWT_PASSWD"]
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
app.config["JWT_ACCESS_COOKIE_PATH"] = "/flask/"
app.config["JWT_COOKIE_CSRF_PROTECT"] = False
jwt = JWTManager(app)


@app.route("/flask/signup", methods=["POST"])
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

@app.route('/flask/user_type', methods=["GET"])
@fresh_jwt_required
def getUserType():
  username = get_jwt_identity()  
  return jsonify({"status": 200, "access_level": logins.get_user_access_level(username)})

@app.route('/flask/login', methods=['POST'])
def login():
    if not request.is_json:
        return jsonify({"msg": "Incorrect username or password. Please try again."})

    login = request.json
    username = login.get("username", None)
    password = login.get("password", None)
    authorise = False

    if username and password:
        authorise = logins.verify_user(username, password)

    if authorise:
        access_token = create_access_token(identity=username, fresh=True)
        response = jsonify({"status": 200, "access_token": access_token})
        set_access_cookies(response, access_token)

        return response
    else:
        return jsonify({"status": 400, "msg": "Incorrect username or password. Please try again."})

    logger.Log(log.LogType.Website, str(request), user=username)


@app.route("/flask/authorised", methods=["GET"])
@fresh_jwt_required
def authorised():
    username = get_jwt_identity()

    return jsonify({"status": 200, "msg": "User authorised."})

@app.route('/flask/getmyworkflows', methods=['GET'])
@pny.db_session
@fresh_jwt_required
def getMyWorkflows():
    username = get_jwt_identity()
    return json.dumps(logins.get_allowed_workflows(username)) 


@app.route('/flask/createincident', methods=['POST'])
@jwt_required
def createIncident():
    incident_request = request.json
    creator = get_jwt_identity()
    incident_name=incident_request.get("incidentName", None)
    incident_kind=incident_request.get("incidentType", None)
    if incident_name and incident_kind:
        job_id = incidents.createIncident(incident_name, incident_kind, creator)
        logger.Log(log.LogType.Website, ("Creation of incident kind %s of name %s by %s" % (incident_name, incident_kind, creator)), user=creator)
        return jsonify({"status": 201, "msg": "Incident successfully created.", "incidentid" : job_id})    
    else:
        return jsonify({"status": 400, "msg": "Incident name or type is missing"})


@app.route('/flask/getincidents', methods=['GET'])
@pny.db_session
@fresh_jwt_required
def getAllMyIncidents():    
    username = get_jwt_identity()    
    return jsonify({"status": 200, "incidents": json.dumps(incidents.retrieveMyIncidents(username))})
    #return jsonify({"status": 401, "msg": "Error retrieving user incidents."})


@app.route('/flask/incident/<incident_uuid>', methods=['GET'])
@pny.db_session
@fresh_jwt_required
def getSpecificIncident(incident_uuid):
    user = get_jwt_identity()
    incident_info=incidents.retrieveIncident(incident_uuid, user)

    if (incident_info is None):
        logger.Log(log.LogType.Website, "User %s raised error retrieving incident %s" % (user, incident_uuid), user=user)
        return jsonify({"status": 401, "msg": "Error retrieving incident."})
    else:
        return jsonify({"status": 200, "incident": json.dumps(incident_info)})

@app.route('/flask/activateincident/<incident_uuid>', methods=['GET'])
@pny.db_session
@fresh_jwt_required
def activateIncident(incident_uuid):    
    user = get_jwt_identity()
    retval=incidents.activateIncident(incident_uuid, user)    

    if (retval):
        logger.Log(log.LogType.Website, "User %s activated incident %s" % (user, incident_uuid), user=user)
        return jsonify({"status": 200, "msg": "Incident activated"})         
    else:
        logger.Log(log.LogType.Website, "User %s raised error activating incident %s" % (user, incident_uuid), user=user)
        return jsonify({"status": 401, "msg": "Error retrieving incident."})


@app.route('/flask/logs', methods=['GET'])
@pny.db_session
@fresh_jwt_required
@logins.admin_required
def showLogs():
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

    return json.dumps(logs)

def getHealthOfComponent(component_name, displayname):
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

@app.route('/flask/health', methods=['GET'])
@pny.db_session
@fresh_jwt_required
@logins.admin_required
def getHealth():
    component_healths=[]    
    component_healths.append(getHealthOfComponent(EDI_URL, "External data interface"))    
    component_healths.append(getHealthOfComponent(JOB_MANAGER_URI, "Simulation manager"))    
    return json.dumps(component_healths)

@app.route('/flask/deleteworkflow', methods=['POST'])
@pny.db_session
@fresh_jwt_required
@logins.admin_required
def deleteWorkflow():
    wf_data = request.json
    kind = wf_data.get("kind", None)
    item=RegisteredWorkflow.get(kind=kind)
    item.delete()
    pny.commit()    
    return jsonify({"status": 200, "msg": "Workflow deleted"})


@app.route('/flask/workflowinfo', methods=['GET'])
@pny.db_session
@fresh_jwt_required
@logins.admin_required
def getWorkflowInfo():
    workflow_info=[]    
    registeredworkflows=pny.select(registeredworkflow for registeredworkflow in RegisteredWorkflow)
    for workflow in registeredworkflows:
        lg={}
        lg["kind"]=workflow.kind
        lg["queuename"]=workflow.init_queue_name
        workflow_info.append(lg)
    return json.dumps(workflow_info)
    

@app.route('/flask/addworkflow', methods=['POST'])
@pny.db_session
@fresh_jwt_required
@logins.admin_required
def addWorkflow():
    wf_data = request.json
    kind = wf_data.get("kind", None)
    queuename = wf_data.get("queuename", None)
    newwf = RegisteredWorkflow(kind=kind, init_queue_name=queuename)

    pny.commit()    
    return jsonify({"status": 200, "msg": "Workflow added"})

@app.route('/flask/getallusers', methods=['GET'])
@pny.db_session
@fresh_jwt_required
@logins.admin_required
def getAllUsers():
    return json.dumps(logins.get_all_users())

@app.route('/flask/getuser', methods=['POST'])
@pny.db_session
@fresh_jwt_required
@logins.admin_required
def getUserDetails():
    user_data = request.json
    return json.dumps(logins.get_user_details(user_data.get("username", None)))    

@app.route('/flask/edituser', methods=['POST'])
@pny.db_session
@fresh_jwt_required
@logins.admin_required
def editUserDetails():
    user_data = request.json    
    username = user_data.get("username", None)
    stored_user=User.get(username=username)
    stored_user.name=user_data.get("name", None)
    stored_user.email=user_data.get("email", None)
    if user_data.get("type", None)=="user":
        stored_user.access_rights=0
    elif user_data.get("type", None)=="administrator":
        stored_user.access_rights=1
    stored_user.enabled=user_data.get("enabled", None)    
    pny.commit()    
    return jsonify({"status": 200, "msg": "User edited"})

@app.route('/flask/addusertoworkflow', methods=['POST'])
@pny.db_session
@fresh_jwt_required
@logins.admin_required
def addUserToWorkflow():
    user_data = request.json    
    username = user_data.get("username", None)
    workflow_kind = user_data.get("workflow", None)
    user=User.get(username=username)
    workflow=RegisteredWorkflow.get(kind=workflow_kind)
    user.allowed_workflows.add(workflow)
    pny.commit()    
    return jsonify({"status": 200, "msg": "Workflow added"})   

@app.route('/flask/removeuserfromworkflow', methods=['POST'])
@pny.db_session
@fresh_jwt_required
@logins.admin_required
def removeUserFromWorkflow():
    user_data = request.json    
    username = user_data.get("username", None)
    workflow_kind = user_data.get("workflow", None)[0]    
    user=User.get(username=username)    
    for item in user.allowed_workflows:        
        if (item.kind == workflow_kind):            
            user.allowed_workflows.remove(item);
    pny.commit()    
    return jsonify({"status": 200, "msg": "Workflow removed"})


@app.route("/flask/logout", methods=["DELETE"])
def logout():
    response = jsonify({"status": 200, "msg": "User logged out."})
    unset_jwt_cookies(response)

    return response


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)

