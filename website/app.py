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
from Database.users import User
from Database.job import Job
from Database.queues import Queue
from Database.machine import Machine
from Database.activity import Activity
from pony.orm.serialization import to_dict
from flask import Flask, render_template, request, jsonify
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity

# Initialise database
Database.initialiseDatabase()

# Initialise services
app = Flask(__name__)  # create an instance if the imported Flask class
logger = log.VestecLogger("Website")

if "VESTEC_MANAGER_URI" in os.environ:
    TARGET_URI = os.environ["VESTEC_MANAGER_URI"]
else:
    TARGET_URI = 'http://127.0.0.1:5500/jobs'

# Initialise JWT
app.config["JWT_SECRET_KEY"] = os.environ["JWT_PASSWD"]
jwt = JWTManager(app)


@app.route("/flask/signup", methods=["POST"])
def signup():
    if not request.is_json:
        return jsonify({"msg": "Required JSON not found in request"}), 400

    user = request.json
    username = user.get("username", None)
    name = user.get("name", None)
    email = user.get("email", None)
    password = user.get("password", None)

    user_create = logins.add_user(username, name, email, password)

    if user_create == "True":
        msg = "Account created for user %s" % username
        logger.Log(log.LogType.Logins, msg, user=username)

        return "True"
    else:
        return "False"


@app.route('/flask/login', methods=['POST'])
def login():
    logger.Log(log.LogType.Website,str(request))

    if not request.is_json:
        return jsonify({"msg": "Required JSON not found in request"}), 400  

    login = request.json
    username = login.get("username", None)
    password = login.get("password", None)
    authorise = False

    if username and password:
        authorise = logins.verify_user(username, password)

    if authorise:
        access_token = create_access_token(identity=username)
        return jsonify(access_token=access_token)
    else:
        return jsonify({"msg": "Incorrect username or password"})  


@app.route('/flask/submit', methods=['PUT'])
@jwt_required
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
    job = request.json
    job["creator"] = get_jwt_identity() 
    job["job_id"] = str(uuid4())

    job_request = requests.put(TARGET_URI + '/' + job["job_id"], json=job)
    response = job_request.text

    logger.Log(log.LogType.Website, "Creation of activity %s is %s" % (job["job_name"], response))

    return response


@app.route('/flask/jobs', methods=['GET'])
@pny.db_session
@jwt_required
def check_all_jobs_status():
    '''This function sends a GET request to the database for the details of all jobs'''
    user = User.get(name = get_jwt_identity())
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

    return json.dumps(activities)


@app.route("/flask/logs")
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


#removes the user's jwt from the authorised list (essentially logs the user out)
@app.route("/logout", methods=["DELETE"])
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
@app.route("/secret")
@logins.login_required
def secret():
    return jsonify({"msg":"Token works!"})

#tests if a user has authentication
@app.route("/supersecret")
@logins.admin_required
def supersecret():
    return jsonify({"msg":"You are an admin"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)

