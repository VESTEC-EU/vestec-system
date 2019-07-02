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
from Database.job import SubmittedJobStatus, SubmittedActivityStatus
import datetime
from uuid import uuid4
import ConnectionManager
import Templating
import Utils.log as log


app=flask.Flask("Simulation Manager")

logger = log.VestecLogger("Simulation Manager")


@app.route("/")
def WelcomePage():
    logger.Log(type=log.LogType.Query,comment=str(request))
    return("VESTEC simulation manager")



#Return a json of the properties of all jobs
@app.route("/jobs")
def JobSummary():
    logger.Log(type=log.LogType.Query,comment=str(request))
    Tasks=[]
    #get all activities, loop through them and create dictionaries to store the information
    with pny.db_session:
        activities = pny.select(a for a in Database.job.Activity)[:]
        for a in activities:
            name = a.getName()
            uuid=a.getUUID()
            sjbs = a.getSubmittedJobs()

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


    return json.dumps(Tasks,indent=4)



#submit (PUT) or view info on a submitted job (GET)

@app.route("/jobs/<jobID>",methods=["GET","PUT"])
@pny.db_session
def RunJob(jobID):
    logger.Log(type=log.LogType.Activity,comment=str(request))

    if flask.request.method == "GET":
        a = Database.job.Activity.get(uuid=jobID)
        if a== None:
            return json.dumps({})
        else:
            name = a.getName()
            sjbs = a.getSubmittedJobs()
            juuid = a.getUUID()
            jobs=[]
            #print("JOB=",sjbs)
            jbs = pny.select(j for j in sjbs)[:]
            for jb in jbs:
                machine = jb.getMachine().name
                status=jb.getStatus().name
                exe=jb.getExecutable()
                qid=jb.getQueueId()

                job={}
                job["machine"] = machine
                job["status"] = status
                job["executable"] = exe
                job["QueueID"] = qid

                jobs.append(job)

            act={}
            act["Name"] = name
            act["jobs"] = jobs
            act["date"] = str(a.getDate())
            act["status"] = a.getStatus().name
            act["UUID"] = juuid

            return(json.dumps(act))


    elif flask.request.method == "PUT":
        print("jobID = %s"%jobID)
        data = dict=flask.request.get_json()

        name=data["name"]

        newActivity = Database.job.Activity(name=name,uuid=jobID,date=datetime.datetime.now())

        pny.commit()

        #put some code in here to determine machine to run the job on, job parameters etc

        #kick off a thread to "manage" this job. In reality it just changes the status a few times and exits
        t=threading.Thread(target=task,args=(jobID,),name=jobID)
        t.start()

        return jobID






#Displays a simple HTML page with the currently active threads
@app.route("/threads")
def ThreadInfo():
    logger.Log(type=log.LogType.Query,comment=str(request))
    string="<h1> Active threads </h1>"
    for t in threading.enumerate():
        string+="\n <p> %s </p>"%t.name
    return string



# task to be run in a thread for each job. Currently just changes the job status then exits
@pny.db_session
def task(JobID):
    act = Database.job.Activity.get(uuid=JobID)
    machine = Database.machine.Machine.get(name="ARCHER")
    logger.Log(type=log.LogType.Activity,comment="Selected machine %s for activity %s"%(machine.name,JobID))
    time.sleep(3)

    act.setStatus(SubmittedActivityStatus.ACTIVE)
    ID = str(uuid4())
    job=act.addSubmittedJob(uuid=ID,machine=machine,executable="test.exe",queue_id="Q341592",wkdir="/work/files")
    logger.Log(type=log.LogType.Job,comment="Submitted job %s for activity %s"%(ID,JobID))
    pny.commit()
    time.sleep(10)

    job.updateStatus(SubmittedJobStatus.RUNNING)
    logger.Log(type=log.LogType.Job,comment="Job %s running for activity %s"%(ID,JobID))
    pny.commit()
    time.sleep(10)

    act.setStatus(SubmittedActivityStatus.COMPLETED)
    logger.Log(type=log.LogType.Job,comment="Job %s completed for activity %s"%(ID,JobID))
    job.updateStatus(SubmittedJobStatus.COMPLETED)
    logger.Log(type=log.LogType.Activity,comment="Activity %s completed"%(JobID))
    return







if __name__ == "__main__":
    Database.initialiseDatabase()
    app.run(host="0.0.0.0",port=5500)
