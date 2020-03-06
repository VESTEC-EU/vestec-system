import pony.orm as pny
from db import Simulation, initialise_database
import uuid
import QueueParsing.pbs as pbs
import time
import workflow
from ConnectionManager import RemoteConnection

@pny.db_session
def Create(incident):
    id=str(uuid.uuid4())

    Simulation(uuid=id,incident=incident)

    return id

@pny.db_session
def SetResultsHandler(id,handler):
    sim = Simulation[id]
    sim.results_handler = handler


@pny.db_session
def SetMachine(id,machine,queue,wkdir):
    sim= Simulation[id]
    
    sim.machine=machine
    sim.queue = queue
    sim.wkdir = wkdir

@pny.db_session
def SetJobProperties(id,nodes,walltime):
    sim= Simulation[id]
    sim.nodes = nodes
    sim.walltime = walltime

@pny.db_session
def SetJobID(id,JobID):
    sim= Simulation[id]
    sim.jobID = JobID

@pny.db_session
def UpdateSimulationStatus(id,status):
    sim= Simulation[id]
    sim.status = status




#Gets all jobs from the database that have not completed
@pny.db_session
def GetActiveJobs():
    jobs = pny.select(j for j in Simulation if j.status == "SUBMITTED" or j.status=="RUNNING" or j.status=="EXITING")[:]
    ids=[]
    for j in jobs:
        ids.append(j.jobID)
    return ids

#For a list of JobIDs, queries the HPC machine for their status and returns this
def GetJobInfo(machine,jobIDs):
    if (len(jobIDs)==0):
        print("No jobs in database... doing nothing")
        return []

    print(jobIDs)
    
    #open connection to HPC machine
    c = RemoteConnection(machine)
    
    #construct string for the command to be executed on the machine (qstat -fx [jobids])
    jobstr=""
    for job in jobIDs:
        jobstr += job+" "

    command = "qstat -fx %s"%jobstr
    
    #execute the command
    stdout,stderr,exit_status=c.ExecuteCommand(command)
    
    #parse the output from qstat into dictionaries
    qstat = (stdout).splitlines(True)
    jobs=pbs.Parse(qstat)
    
    #close the remote connection
    c.CloseConnection()

    return jobs
    
#Check the status of the jobs, updating the simulations in the database to reflect this
@pny.db_session
def CheckJobStatuses(jobs):
    for job in jobs:
        id = job["JobID"]
        status = job["job_state"]
        sim = Simulation.get(lambda s: id in s.jobID)
        print(id, status)
        if status == "Q":
            sim.status = "SUBMITTED"
        elif status == "R":
            sim.status = "RUNNING"
        elif status == "E":
            sim.status = "EXITING"
        elif status == "F":
            #TODO CHECK FOR EXIT CODE FROM JOB - DID IT SUCCEED OR DID IT FAIL
            sim.status = "COMPLETED"
            #now send a message to tell the workflow that the simulation is finsihed
            NotifyWorkflowOfCompletion(sim)
        else:
            sim.STATUS = "UNKNOWN %s"%status

@pny.db_session
def NotifyWorkflowOfCompletion(sim):
         workflow.OpenConnection()
         handler = sim.results_handler

         message={}
         message["IncidentID"] = sim.incident.uuid
         message["wkdir"] = sim.wkdir
         message["SimID"] = sim.uuid
         message["machine"] = sim.machine

         workflow.send(message,handler)
         workflow.FlushMessages()
         workflow.CloseConnection()




if __name__ == "__main__":
    machine = "ARCHER"

    while True:
        IDs=GetActiveJobs()
        jobs=GetJobInfo(machine,IDs)
        CheckJobStatuses(jobs)
        #We need to use the rabbitmq connection.sleep command 
        # to prevent it from ignoring heartbeat checks from the 
        # rmq broker else the broker can terminate the connection
        #workflow.connection.sleep(60)
        time.sleep(60)



    