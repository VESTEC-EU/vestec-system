#!/usr/local/bin/flask
'''render_template loads html pages of the application
'''
import sys
sys.path.append("../")
import os
import uuid
import json
import requests
import pony.orm as pny
import Utils.log as log
import Database
import flask_jwt_extended as jwt
import datetime
from website import logins
from Database.users import User
from Database.job import Job
from Database.queues import Queue
from Database.machine import Machine
from Database.activity import Activity
from pony.orm.serialization import to_dict
from flask import Flask, render_template, request, jsonify


Database.initialiseDatabase()
logger=log.VestecLogger("Website")

APP = Flask(__name__)  # create an instance if the imported Flask class
APP.config["JWT_SECRET_KEY"] = "SECRET"

JWT=jwt.JWTManager(APP)


if "VESTEC_MANAGER_URI" in os.environ:
    TARGET_URI = os.environ["VESTEC_MANAGER_URI"]
else:
    TARGET_URI = 'http://127.0.0.1:5500/jobs'

CURRENT_JOB = {'job_id': '', 'job_name': ''}

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
    CURRENT_JOB = request.json
    CURRENT_JOB["job_id"] = generate_id()

    job_request = requests.put(TARGET_URI + '/' + CURRENT_JOB["job_id"], json=CURRENT_JOB)
    response = job_request.text

    logger.Log(log.LogType.Website, "Creation of activity %s is %s" % (CURRENT_JOB["job_name"], response))

    return response


@APP.route('/flask/jobs', methods=['GET'])
@pny.db_session
def check_all_jobs_status():
    '''This function sends a GET request to the database for the details of all jobs'''
    user = User.get(name="Vestec")
    #activity_records = user.activities  # this returns user, activities and jobs
    activity_records = pny.select(a for a in Activity if a.user_id==user)[:]
    activities = {}

    for i,a in enumerate(activity_records):
        activity = a.to_dict()
        activity.pop("user_id")
        activity_date = a.date_submitted.strftime("%d/%m/%Y, %H:%M:%S")
        activity["date_submitted"] = activity_date
        activity_jobs = a.jobs
        jobs = []

        for job in activity_jobs:
            job_dict = job.to_dict()
            job_dict["machine"] = job.queue_id.machine_id.machine_name
            job_dict["submit_time"] = job.submit_time.strftime("%d/%m/%Y, %H:%M:%S")

            if job.end_time is not None:
                job_dict["run_time"] = str(job.run_time)
                job_dict["end_time"] = job.end_time.strftime("%d/%m/%Y, %H:%M:%S")

            jobs.append(job_dict)

        activity["jobs"] = jobs

        activities["activity" + str(i)] = activity

    logger.Log(log.LogType.Website, "User %s is trying to extract %s activities" % (user.username, len(activities)))

    serialised_dates = {key: str(value) for key, value in activities.items()}
    logger.Log(log.LogType.Website, "%s activities had their dates converted to strings" % (len(serialised_dates),))

    return json.dumps(serialised_dates)


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


@APP.route("/flask/signup", methods=["POST"])
def signup():
    user = request.json
    username = user["username"]
    name = user["name"]
    email = user["email"]
    password = user["password"]

    user_create = logins.AddUser(username, name, email, password)

    if user_create == "True":
        msg = "Account created for user %s" % username
        logger.Log(log.LogType.Logins, msg, user=username)

        return "True"
    else:
        return "False"

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

if __name__ == '__main__':
    if "VESTEC_MANAGER_URI" in os.environ:
        TARGET_URI = os.environ["VESTEC_MANAGER_URI"]

    print("Website using SimulationManager URI: %s"%TARGET_URI)
    APP.run(host='0.0.0.0', port=8000)
