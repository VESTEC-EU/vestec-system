#!/usr/local/bin/flask
'''render_template loads html pages of the application
'''
import sys
sys.path.append("../")
import os
import uuid
import json
import requests
from flask import Flask, render_template, request, jsonify
import Utils.log as log
import Database
from website import logins
import flask_jwt_extended as jwt
import datetime


import pony.orm as pny

Database.initialiseDatabase()
logger=log.VestecLogger("Website")

APP = Flask(__name__)  # create an instance if the imported Flask class
APP.config["JWT_SECRET_KEY"] = "SECRET"

JWT=jwt.JWTManager(APP)


if "VESTEC_MANAGER_URI" in os.environ:
    TARGET_URI = os.environ["VESTEC_MANAGER_URI"]
else:
    TARGET_URI = 'http://127.0.0.1:5500/jobs'

CURRENT_JOB = {'uuid': '', 'name': ''}

def generate_id():
    '''auto-generates a uuid'''
    return str(uuid.uuid1())


@APP.route('/flask/auth')  # used to bind the following function to the specified URL
def welcome_page():
    '''Render a static welcome template'''
    print("TARGET_URI = %s"%TARGET_URI)
    logger.Log(log.LogType.Website,str(request))
    return "real"


@APP.route('/flask/submit', methods=['PUT'])
def submit_job():
    '''This function sends a PUT request to the SMI for a CURRENT_JOB
       to be created

       Process:
       - generate CURRENT_JOB object
       - send CURRENT_JOB object as JSON to the SMI server
       - if the SMI server has received the JSON package, return string message

       Input Params: none
       Output Params: response_data - SMI response string

       Data Structures:
       - SMI URI: /jobs/uuid
       - CURRENT_JOB object: {'uuid': <id>, 'name': <title>}
       - SMI response data: 'SUCCESS' or 'FAILURE'
    '''
    CURRENT_JOB['uuid'] = generate_id()
    CURRENT_JOB['name'] = request.form.get('jsdata')

    job_request = requests.put(TARGET_URI + '/' + CURRENT_JOB.get('uuid'), json=CURRENT_JOB)
    response_data = job_request.text
    logger.Log(log.LogType.Website,str(request))

    return response_data


@APP.route('/flask/jobs/current', methods=['GET'])
def check_job_status():
    '''This function sends a GET request to the SMI for the details of the current job

       Process:
       - send get request to the SMI passing the current job as parameter
       - get SMI response job dictionary
       - render SMI response on table template

       Input Params: none
       Output Params: response_data - SMI response dictionary

       Data Structures:
       - SMI URI: /jobs/uuid
       - SMI response data: {"uuid": <jobuuid>, "name": <jobname>,
                             "jobs": [{"machine": <machinename>,
                                       "status": <jobstatus>, "executable": <exec>,
                                       "QueueID": <queueid>}, {}],
                             "date": <jobsubmitdate>, "status": <jobstatus>}
    '''
    current_stat_req = requests.get(TARGET_URI + '/' + str(CURRENT_JOB.get('uuid')))
    response_data = current_stat_req.json()
    logger.Log(log.LogType.Website,str(request))

    return json.dumps(response_data)


@APP.route('/flask/jobs', methods=['GET'])
def check_all_jobs_status():
    '''This function sends a GET request to the SMI for the details of all jobs

       Process:
       - send get request to the SMI for all jobs
       - get SMI response jobs dictionary of dictionaries
       - render SMI response on table template

       Input Params: none
       Output Params: response_data - SMI response dictionary

       Data Structures:
       - SMI URI: /jobs
       - SMI response data: [{"uuid": <jobuuid>, "name": <jobname>,
                              "jobs": [{"machine": <machinename>,
                                        "status": <jobstatus>, "executable": <exec>,
                                        "QueueID": <queueid>}, {}
                              ], "date": <jobsubmitdate>, "status": <jobstatus>}, {}]
    '''
    all_stat_req = requests.get(TARGET_URI)
    response_data = all_stat_req.json()
    logger.Log(log.LogType.Website,str(request))

    return json.dumps(response_data)


@APP.route("/flask/logs")
def showLogs():
    logs=[]
    with pny.db_session:
        ls=pny.select(a for a in log.DBLog)[:]
        for l in ls:
            lg={}
            lg["timestamp"]=str(l.timestamp)
            lg["originator"]=l.originator
            lg["user"]=l.user
            lg["type"] = l.type.name
            lg["comment"] = l.comment
            logs.append(lg)
    return logs


@APP.route("/signup",methods=["GET","POST"])
def signup():
    if request.method=="GET":
        return render_template("signup.html")
    else:
        username = request.form["username"]
        name = request.form["name"]
        password = request.form["password"]
        email = request.form["email"]

        if logins.AddUser(username,name,email,password):
            msg = "Account created for user %s"%username
            logger.Log(log.LogType.Logins,msg,user=username)
            return render_template("signup.html",success=True,user=username)
        else:
            return render_template("signup.html", success=False)


#old HTML-only login page
@APP.route("/login2",methods=["GET","POST"])
def loginpage():
    if request.method == "GET":
        return render_template("login.html")
    else:
        username=request.form["username"]
        password=request.form["password"]

    if logins.VerifyUser(username,password):
        with pny.db_session:
            user = Database.User.get(username=username)
            name = user.name
        return render_template("login.html",success=True,name=name)
    else:
        return render_template("login.html",success=False)

#new login page (with javascript and some jwt test functionalty)
@APP.route("/login")
def login():
    return render_template("auth.html")


#checks if a user is authorised, and if so, gives them a jwt
@APP.route("/authenticate",methods=["POST"])
def auth():
    username = request.json.get('username', None)
    password = request.json.get('password', None)
    print("user = %s"%username)

    if logins.VerifyUser(username,password):
        with pny.db_session:
            user = Database.User.get(username=username)
            name = user.name
            token = jwt.create_access_token(identity=username)
            print("JWT= %s"%token)
            jti = jwt.get_jti(token)
            now=datetime.datetime.now()
            userToken = Database.Token(jti=jti,date_created=now,date_accessed=now,user=user)
            msg = "User %s logged in"%username
            logger.Log(log.LogType.Logins,msg,user=username)
            return jsonify({"token":token})
    
    else:
        return jsonify({"msg":"Error: Invalid user"})

#removes the user's JWT from the authorised list (essentially logs the user out)
@APP.route("/logout", methods=["DELETE"])
@logins.login_required
def logout():
    #get the jti
    jti = jwt.get_raw_jwt()["jti"]
    username=jwt.get_jwt_identity()
    with pny.db_session:
        token = Database.Token.get(jti=jti)
        token.delete()
        msg = "User %s logged out"%username
        logger.Log(log.LogType.Logins,msg,user=username)
    return jsonify(msg="User logged out")

#tests if a user has a valid jwt
@APP.route("/secret")
@logins.login_required
def secret():
    return jsonify({"msg":"Token works!"})

#tests if a user has authentication
@APP.route("/supersecret")
@logins.admin_required
def supersecret():
    return jsonify({"msg":"You are an admin"})

@APP.errorhandler(404)
def page_not_found(e):
    '''Handling 404 errors by showing template'''
    logger.Log(log.LogType.Error,"404 Not Found: "+str(request))
    return render_template('404.html'), 404


@APP.errorhandler(500)
def page_not_found(e):
    '''Handling 500 errors by showing template'''
    logger.Log(log.LogType.Error,"500 Internal server error: "+str(request)+str(e))
    return render_template('500.html'), 500


if __name__ == '__main__':
    if "VESTEC_MANAGER_URI" in os.environ:
        TARGET_URI = os.environ["VESTEC_MANAGER_URI"]
    print("Website using SimulationManager URI: %s"%TARGET_URI)
    APP.run(host='0.0.0.0', port=8000)
