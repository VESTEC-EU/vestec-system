#!/usr/local/bin/flask
import sys
import os
sys.path.append("../")
import json
import requests
import pony.orm as pny
import Database
from ExternalServices import logins
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, fresh_jwt_required, get_jwt_identity, set_access_cookies, unset_jwt_cookies
import managementAPI

# Initialise database
Database.initialiseDatabase()

# Initialise services
app = Flask(__name__)  # create an instance if the imported Flask class

# Initialise JWT
app.config["JWT_SECRET_KEY"] = os.environ["JWT_PASSWD"]
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
app.config["JWT_ACCESS_COOKIE_PATH"] = "/flask/"
app.config["JWT_COOKIE_CSRF_PROTECT"] = False
jwt = JWTManager(app)

@app.route('/flask/version', methods=["GET"])
def getVersion():
    return managementAPI.version()

@app.route("/flask/signup", methods=["POST"])
def signup():
    return managementAPI.signup()

@app.route('/flask/user_type', methods=["GET"])
@fresh_jwt_required
def getUserType():
  username = get_jwt_identity()  
  return managementAPI.getUserType(username)  

@app.route('/flask/login', methods=['POST'])
def login():
    return managementAPI.login()

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
    return managementAPI.getMyWorkflows(username)


@app.route('/flask/createincident', methods=['POST'])
@jwt_required
def createIncident():
    username = get_jwt_identity()
    return managementAPI.createIncident(username)

@app.route('/flask/getincidents', methods=['GET'])
@pny.db_session
@fresh_jwt_required
def getAllMyIncidents():
    username = get_jwt_identity()
    pending_filter = request.args.get("pending", "false").lower() == "true"
    active_filter = request.args.get("active", "false").lower() == "true"
    completed_filter = request.args.get("completed", "false").lower() == "true"
    cancelled_filter = request.args.get("cancelled", "false").lower() == "true"
    error_filter = request.args.get("error", "false").lower() == "true"
    archived_filter = request.args.get("archived", "false").lower() == "true"

    return managementAPI.getAllMyIncidents(username, pending_filter, active_filter, completed_filter, cancelled_filter, error_filter, archived_filter)    

@app.route('/flask/incident/<incident_uuid>', methods=['GET'])
@pny.db_session
@fresh_jwt_required
def getSpecificIncident(incident_uuid):
    username = get_jwt_identity()
    return managementAPI.getSpecificIncident(incident_uuid, username)

@app.route('/flask/incident/<incident_uuid>', methods=['DELETE'])
@pny.db_session
@fresh_jwt_required
def cancelSpecificIncident(incident_uuid):
    username = get_jwt_identity()
    return managementAPI.cancelSpecificIncident(incident_uuid, username)

@app.route('/flask/archiveincident/<incident_uuid>', methods=['GET'])
@pny.db_session
@fresh_jwt_required
def archiveIncident(incident_uuid):    
    username = get_jwt_identity()
    return managementAPI.archiveIncident(incident_uuid, username)

@app.route('/flask/activateincident/<incident_uuid>', methods=['GET'])
@pny.db_session
@fresh_jwt_required
def activateIncident(incident_uuid):    
    username = get_jwt_identity()
    return managementAPI.activateIncident(incident_uuid, username)

@app.route('/flask/data/<data_uuid>', methods=['GET'])
@pny.db_session
@fresh_jwt_required
def downloadData(data_uuid):
    return managementAPI.downloadData(data_uuid)


@app.route('/flask/logs', methods=['GET'])
@pny.db_session
@fresh_jwt_required
@logins.admin_required
def getLogs():
    return managementAPI.getLogs()

@app.route('/flask/health', methods=['GET'])
@pny.db_session
@fresh_jwt_required
@logins.admin_required
def getHealth():
    return managementAPI.getComponentHealths()

@app.route('/flask/deleteworkflow', methods=['POST'])
@pny.db_session
@fresh_jwt_required
@logins.admin_required
def deleteWorkflow():    
    return managementAPI.deleteWorkflow(request.json)

@app.route('/flask/workflowinfo', methods=['GET'])
@pny.db_session
@fresh_jwt_required
@logins.admin_required
def getWorkflowInfo():
    return managementAPI.getWorkflowInfo()

@app.route('/flask/addworkflow', methods=['POST'])
@pny.db_session
@fresh_jwt_required
@logins.admin_required
def addWorkflow():
    return managementAPI.addWorkflow(request.json)

@app.route('/flask/getallusers', methods=['GET'])
@pny.db_session
@fresh_jwt_required
@logins.admin_required
def getAllUsers():
    return managementAPI.getAllUsers()

@app.route('/flask/getuser', methods=['POST'])
@pny.db_session
@fresh_jwt_required
@logins.admin_required
def getUserDetails():    
    return managementAPI.getUserDetails(request.json)    

@app.route('/flask/edituser', methods=['POST'])
@pny.db_session
@fresh_jwt_required
@logins.admin_required
def editUserDetails():    
    return managementAPI.editUserDetails(request.json)

@app.route('/flask/addusertoworkflow', methods=['POST'])
@pny.db_session
@fresh_jwt_required
@logins.admin_required
def addUserToWorkflow():
    return managementAPI.addUserToWorkflow(request.json)

@app.route('/flask/removeuserfromworkflow', methods=['POST'])
@pny.db_session
@fresh_jwt_required
@logins.admin_required
def removeUserFromWorkflow():    
   return managementAPI.removeUserFromWorkflow(request.json)

@app.route("/flask/logout", methods=["DELETE"])
def logout():
    response = jsonify({"status": 200, "msg": "User logged out."})
    unset_jwt_cookies(response)
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)

