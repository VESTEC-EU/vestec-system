from __future__ import print_function
import sys
sys.path.append("../")
import flask
from flask import request
import threading
import time
import json
import pony.orm as pny
from Database import initialiseDatabase
from Database.generate_db import initialiseStaticInformation
from Database.machine import Machine
from Database.queues import Queue
from Database.users import User
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


@app.route("/jobs/<activity_id>", methods=["PUT"])
@pny.db_session
def create_activity(activity_id):    
    data = dict=flask.request.get_json()
    name = data["job_name"]

    activity_creation = ""

    try:        
        user = User.get(name="Vestec")
        user.activities.create(activity_id=activity_id, activity_name=name,
                               date_submitted=datetime.datetime.now(), activity_type="to be developed",
                               location="to be developed")

        pny.commit()

        #kick off a thread to "manage" this job. In reality it just changes the status a few times and exits
        thread = threading.Thread(target=task, args=(activity_id,), name=activity_id)
        thread.start()

        activity_creation = "True"
    except Exception as e:
        activity_creation = "False"

    return activity_creation


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
    activity = Activity.get(activity_id=activity_id)
    logger.Log(type=log.LogType.Activity, comment="Creating job for activity %s with id %s" % (activity.activity_name, activity_id))

    queue = Queue.get(queue_name="standard")
    logger.Log(type=log.LogType.Activity, comment="Selected queue %s for activity %s" % (queue.queue_id, activity.activity_name))

    time.sleep(3)
    job_id = str(uuid4()) 

    try:
        job = Job(job_id=job_id, activity_id=activity, queue_id=queue, no_nodes=1, walltime=300, submit_time=datetime.datetime.now(), executable="test.exe", work_directory="/work/files")
        activity.jobs.add(job)
        queue.jobs.add(job)
        activity.setStatus("ACTIVE")
        pny.commit()

        start_time = time.time()
        logger.Log(type=log.LogType.Job, comment="Created job %s for activity %s on queue %s" % (job_id, activity.activity_name, queue.queue_id))
    except Exception as e:
        activity.setStatus("ERROR")
        logger.Log(type=log.LogType.Job, comment="Job creation failed: " + str(e))

    time.sleep(10)
    job.setStatus("RUNNING")
    logger.Log(type=log.LogType.Job, comment="Job %s running for activity %s" % (job_id, activity_id))
    pny.commit()

    time.sleep(10)
    job.setStatus("COMPLETED")
    job.setRunTime(datetime.timedelta(seconds=start_time - time.time()))
    job.setEndTime(datetime.datetime.now())
    logger.Log(type=log.LogType.Job, comment="Job %s completed for activity %s" % (job_id, activity_id))
    activity.setStatus("COMPLETED")
    logger.Log(type=log.LogType.Activity, comment="Activity %s completed" % (activity_id))

    return


@pny.db_session
def generate_database():
    machine = pny.count(m for m in Machine)
    queues = pny.count(q for q in Queue)

    if (machine == 0) or (queues == 0):
        initialiseStaticInformation()


if __name__ == "__main__":
    initialiseDatabase()
    generate_database()
    app.run(host="0.0.0.0", port=5500)
