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
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, fresh_jwt_required, get_jwt_identity, set_access_cookies, unset_jwt_cookies, get_raw_jwt
import managementAPI
import EDIconnector

# Initialise database
Database.initialiseDatabase()

# Initialise services
app = Flask(__name__)  # create an instance if the imported Flask class

# Initialise JWT
app.config["JWT_SECRET_KEY"] = os.environ["JWT_PASSWD"]
app.config["JWT_TOKEN_LOCATION"] = ["headers"]
app.config['JWT_BLACKLIST_ENABLED'] = True
app.config['JWT_BLACKLIST_TOKEN_CHECKS'] = ['access', 'refresh']
jwt = JWTManager(app)

blacklist = set()

@jwt.token_in_blacklist_loader
def check_if_token_in_blacklist(decrypted_token):
    jti = decrypted_token['jti']
    return jti in blacklist

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

@app.route('/flask/changepassword', methods=['POST'])
@pny.db_session
@fresh_jwt_required
@logins.admin_required
def changePassword():
    return managementAPI.changePassword()    

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

@app.route('/flask/incidentlogs/<incident_uuid>', methods=['GET'])
@pny.db_session
@fresh_jwt_required
def getIncidentLogs(incident_uuid):
    username = get_jwt_identity()
    return managementAPI.getIncidentLogs(incident_uuid, username)    

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

@app.route('/flask/datasets', methods=['GET'])
@pny.db_session
@fresh_jwt_required
def getMatchingDatasets():
    username = get_jwt_identity()
    data_type = request.args.get("type", None)
    incident_uuid = request.args.get("incident_uuid", None)
    return managementAPI.getDataSets(data_type, incident_uuid, username)

@app.route('/flask/metadata', methods=['GET'])
@pny.db_session
@fresh_jwt_required
def getDataMetadata():
    username = get_jwt_identity()
    data_uuid = request.args.get("data_uuid", None)
    incident_uuid = request.args.get("incident_uuid", None)
    return managementAPI.getDataMetadata(data_uuid, incident_uuid, username)

@app.route('/flask/metadata', methods=['POST'])
@pny.db_session
@fresh_jwt_required
def updateDataMetadata():
    username = get_jwt_identity()
    return managementAPI.updateDataMetadata(username)

@app.route('/flask/data/<data_uuid>', methods=['GET'])
@pny.db_session
@fresh_jwt_required
def downloadData(data_uuid):
    return managementAPI.downloadData(data_uuid)

@app.route('/flask/refreshsimulation', methods=['POST'])
@pny.db_session
@fresh_jwt_required
def refreshSimulation():    
    return managementAPI.performRefreshSimulation(request.json)

@app.route('/flask/simulation', methods=['DELETE'])
@pny.db_session
@fresh_jwt_required
def cancelSimulation():
    simulation_uuid = request.args.get("sim_uuid", None)    
    username = get_jwt_identity()  
    return managementAPI.performCancelSimulation(simulation_uuid, username)

@app.route('/flask/data', methods=['DELETE'])
@pny.db_session
@fresh_jwt_required
def deleteData():
    data_uuid = request.args.get("data_uuid", None)
    incident_uuid = request.args.get("incident_uuid", None)
    username = get_jwt_identity()  
    return managementAPI.deleteData(data_uuid, incident_uuid, username)

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

@app.route('/flask/deleteuser', methods=['POST'])
@pny.db_session
@fresh_jwt_required
@logins.admin_required
def deleteUser():    
    return managementAPI.deleteUser(request.json)

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

@app.route('/flask/getediinfo', methods=['GET'])
@pny.db_session
@fresh_jwt_required
@logins.admin_required
def getEDIInfo():    
   return managementAPI.getEDIInfo()

@app.route('/flask/deleteedihandler', methods=['POST'])
@pny.db_session
@fresh_jwt_required
@logins.admin_required
def deleteEDIHandler():    
   return managementAPI.deleteEDIHandler(request.json)

@app.route("/flask/logout", methods=["DELETE"])
@fresh_jwt_required
def logout():
    response = jsonify({"status": 200, "msg": "User logged out."})
    jti = get_raw_jwt()['jti']
    blacklist.add(jti)
    return response

@app.route("/EDI", methods=["POST"])
def post_edi_data_anon():
    return EDIconnector.pushDataToEDI()

@app.route("/EDI/<sourceid>", methods=["POST"])
def post_edi_data(sourceid):    
    return EDIconnector.pushDataToEDI(sourceid)

@app.route('/flask/getmachinestatuses', methods=['GET'])
@pny.db_session
@fresh_jwt_required
@logins.admin_required
def getMachineStatuses():    
   return managementAPI.performRetrieveMachineStatuses()

@app.route('/flask/machine/<machineid>', methods=['DELETE'])
@pny.db_session
@fresh_jwt_required
@logins.admin_required
def deleteMachine(machineid):    
   return managementAPI.performDeleteMachine(machineid)   

@app.route("/flask/addmachine", methods=["POST"])
@pny.db_session
@fresh_jwt_required
@logins.admin_required
def add_new_machine():        
    return managementAPI.performAddNewMachine(request.json)

@app.route("/flask/enablemachine/<machineid>", methods=["POST"])
@pny.db_session
@fresh_jwt_required
@logins.admin_required
def enable_machine(machineid):
    return managementAPI.performEnableMachine(machineid)

@app.route("/flask/disablemachine/<machineid>", methods=["POST"])
@pny.db_session
@fresh_jwt_required
@logins.admin_required
def disable_machine(machineid):
    return managementAPI.performDisableMachine(machineid)

@app.route("/flask/enabletestmodemachine/<machineid>", methods=["POST"])
@pny.db_session
@fresh_jwt_required
@logins.admin_required
def enable_testmode_machine(machineid):
    return managementAPI.enableTestModeMachine(machineid)

@app.route("/flask/disabletestmodemachine/<machineid>", methods=["POST"])
@pny.db_session
@fresh_jwt_required
@logins.admin_required
def disable_test_mode_machine(machineid):
    return managementAPI.disableTestModeMachine(machineid)

if __name__ == '__main__':    
    app.run(host='0.0.0.0', port=8000)    

