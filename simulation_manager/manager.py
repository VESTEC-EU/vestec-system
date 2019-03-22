from __future__ import print_function
import flask
import threading
import time
import json
import database
import pony.orm as pny
from pony.orm.serialization import to_dict
from database.job import SubmittedJobStatus, SubmittedActivityStatus
import datetime


app=flask.Flask("Simulation Manager")


@app.route("/")
def WelcomePage():
    return("VESTEC simulation manager")



#Return a json of the properties of all jobs
@app.route("/jobs")
@pny.db_session
def JobSummary():
    Tasks=[]
    #get all activities, loop through them and create dictionaries to store the information
    activities = pny.select(a for a in database.job.Activity)[:]
    for a in activities:
        name = a.getName()
        sjbs = a.getSubmittedJobs()

        #get all jobs for activity and construct dictionary for each job
        jobs=[]
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

        Tasks.append(act)

    print(json.dumps(Tasks,indent=4))

    return json.dumps(Tasks,indent=4)



#submit (PUT) or view info on a submitted job (GET)

@app.route("/jobs/<jobID>",methods=["GET","PUT"])
@pny.db_session
def RunJob(jobID):

    if flask.request.method == "GET":
        a = database.job.Activity.get(name=jobID)
        if a== None:
            return json.dumps({})
        else:
            name = a.getName()
            sjbs = a.getSubmittedJobs()
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

            return(json.dumps(act))


    elif flask.request.method == "PUT":
        print("jobID = %s"%jobID)
        data = dict=flask.request.get_json()

        newActivity = database.job.Activity(name=jobID,date=datetime.datetime.now())

        pny.commit()

        #put some code in here to determine machine to run the job on, job parameters etc

        #kick off a thread to "manage" this job. In reality it just changes the status a few times and exits
        t=threading.Thread(target=task,args=(jobID,),name=jobID)
        t.start()

        return jobID






#Displays a simple HTML page with the currently active threads
@app.route("/threads")
def ThreadInfo():
    string="<h1> Active threads </h1>"
    for t in threading.enumerate():
        string+="\n <p> %s </p>"%t.name
    return string



# task to be run in a thread for each job. Currently just changes the job status then exits
@pny.db_session
def task(name):
    act = database.job.Activity.get(name=name)
    archer = database.machine.Machine.get(name="ARCHER")
    time.sleep(3)

    act.setStatus(SubmittedActivityStatus.ACTIVE)
    job=act.addSubmittedJob(archer,"test.exe","Q341592","/work/files")
    pny.commit()
    time.sleep(10)

    job.updateStatus(SubmittedJobStatus.RUNNING)
    pny.commit()
    time.sleep(10)

    act.setStatus(SubmittedActivityStatus.COMPLETED)
    job.updateStatus(SubmittedJobStatus.COMPLETED)
    return







if __name__ == "__main__":
    database.initialiseDatabase()
    app.run(host="0.0.0.0",port=5500)
