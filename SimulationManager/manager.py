from __future__ import print_function
import sys
sys.path.append("../")
import flask
from flask import request
import threading
import time
import json
import Database
import pony.orm as pny
from pony.orm.serialization import to_dict
from Database.job import Job, JobStatus
from Database.activity import Activity, ActivityStatus
import datetime
from uuid import uuid4
import ConnectionManager
import Templating
import Utils.log as log


app=flask.Flask("Simulation Manager")
logger = log.VestecLogger("Simulation Manager")

@app.route("/")
def welcome_page():
    logger.Log(type=log.LogType.Query, comment=str(request))
    return("VESTEC simulation manager")

#submit (PUT) or view info on a submitted job (GET)
@app.route("/jobs/<activity_id>", methods=["GET","PUT"])
@pny.db_session
def manage_activity(activity_id):
    logger.Log(type=log.LogType.Activity, comment=str(request))

    if flask.request.method == "GET":
        activity = Activity.get(activity_id=activity_id)

        if activity is not None:
            jobs_tuples = activity.getJobs()
            jobs = []  # list of dicts

            for job in jobs:
                jobs.append(job.to_dict())

            actvity.to_dict()
            actvity["jobs"] = jobs

            return(json.dumps(activity))
        else:
            logger.Log(type=log.LogType.Activity, comment="activity is empty")    
           

    elif flask.request.method == "PUT":
        data = dict=flask.request.get_json()
        name=data["job_name"]

        new_activity = Activity(activity_id=activity_id, activity_name=name,
                                date_submitted=datetime.datetime.now(), activity_type="to be developed",
                                location="to be developed", user="to_be_developed")

        new_activity.setStatus(ActivityStatus.PENDING)

        pny.commit()

        #put some code in here to determine machine to run the job on, job parameters etc

        #kick off a thread to "manage" this job. In reality it just changes the status a few times and exits
        t=threading.Thread(target=task, args=(activity_id,), name=activity_id)
        t.start()

        return activity_id


# Displays a simple HTML page with the currently active threads
@app.route("/threads")
def thread_info():
    logger.Log(type=log.LogType.Query, comment=str(request))
    string = "<h1> Active threads </h1>"

    for t in threading.enumerate():
        string += "\n <p> %s </p>" % t.name

    return string


# task to be run in a thread for each job. Currently just changes the job status then exits
@pny.db_session
def task(activity_id):
    activity = Database.activity.Activity.get(activity_id=activity_id)
    logger.Log(type=log.LogType.Activity, comment="Activating activity %s" % (activity_id, ))
    time.sleep(3)

    activity.setStatus(ActivityStatus.ACTIVE)
    job_id = str(uuid4())
    job = Job(job_id=job_id, no_nodes=1, walltime= 300, submit_time=datetime.datetime.now(), executable="test.exe", work_directory="/work/files")
    job.setStatus(JobStatus.QUEUING)
    
    pny.commit()

    link = ActivityJob(activity_id=activity_id, job_id=job_id, description="to be developed", executable="to be developed")

    logger.Log(type=log.LogType.Job, comment="Submitted job %s for activity %s" % (job_id, activity_id))
    time.sleep(10)

    job.setStatus(JobStatus.RUNNING)
    logger.Log(type=log.LogType.Job, comment="Job %s running for activity %s" % (job_id, activity_id))
    pny.commit()
    time.sleep(10)

    job.updateStatus(JobStatus.COMPLETED)
    logger.Log(type=log.LogType.Job, comment="Job %s completed for activity %s" % (job_id, activity_id))
    activity.setStatus(ActivityStatus.COMPLETED)
    logger.Log(type=log.LogType.Activity, comment="Activity %s completed" % (activity_id))

    return

#Return a json of the properties of all jobs
@app.route("/jobs")
def job_summary():
    logger.Log(type=log.LogType.Query, comment=str(request))

    Tasks=[]
    #get all activities, loop through them and create dictionaries to store the information

    with pny.db_session:
        activities = pny.select(act for act in Database.activity.Activity)[:]

        for activity in activities:
            jobs = a.getSubmittedJobs()

            #get all jobs for activity and construct dictionary for each job
            jobs=[]
            jbs = pny.select(j for j in sjbs)[:]
            for jb in jbs:
                machine = jb.getMachine().name
                status=jb.getStatus().name
                exe=jb.getExecutable()
                qid=jb.getQueueId()
                juuid=jb.getUUID()

                job={}
                job["machine"] = machine
                job["status"] = status
                job["executable"] = exe
                job["QueueID"] = qid
                job["UUID"] = juuid

                jobs.append(job)

            act={}
            act["Name"] = name
            act["UUID"] = uuid
            act["jobs"] = jobs
            act["date"] = str(a.getDate())
            act["status"] = a.getStatus().name

            Tasks.append(act)

    print(json.dumps(Tasks,indent=4))


if __name__ == "__main__":
    Database.initialiseDatabase()
    app.run(host="0.0.0.0",port=5500)
