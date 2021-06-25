from __future__ import print_function
import sys
sys.path.append("../")
sys.path.append("../MachineInterface")
from flask import Flask, request, jsonify
import threading
import time
import json
import pony.orm as pny
from Database import initialiseDatabase
from Database.generate_db import initialiseStaticInformation
from Database.machine import Machine
from Database.queues import Queue
from Database.users import User
from Database.workflow import RegisteredWorkflow, Simulation, Incident
import datetime
from uuid import uuid4
import Utils.log as log
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from WorkflowManager.manager import workflow
from mproxy.client import Client
from MachineStatusManager.client import matchBestMachine, MachineStatusManagerException
import asyncio
import aio_pika
import os

poll_scheduler=BackgroundScheduler(executors={"default": ThreadPoolExecutor(1)})

app = Flask("Simulation Manager")
logger = log.VestecLogger("Simulation Manager")

@app.route("/SM/health", methods=["GET"])
def get_health():
    return jsonify({"status": 200}), 200

@app.route("/SM/info/<simulation_id>",methods=["GET"])
@pny.db_session
def get_sim_info(simulation_id):
    try:
        sim = Simulation[simulation_id]
    except pny.core.ObjectNotFound:
        return "No simulation matching %s found"%simulation_id, 404
    
    d = {}
    d["uuid"] = simulation_id
    d["IncidentID"] = sim.incident.uuid
    d["date_created"] = str(sim.date_created)
    d["status"] = sim.status
    d["status_updated"] = str(sim.status_updated)
    d["directory"] = sim.directory
    d["status_message"] = sim.status_message
    d["machine"] = sim.machine.machine_name
    d["queue"] = sim.queue
    d["jobID"] = sim.jobID
    d["wkdir"] = sim.wkdir
    d["executable"] = sim.executable
    d["kind"] = sim.kind
    d["results_handler"] = sim.results_handler
    d["requested_walltime"] = sim.requested_walltime
    d["walltime"] = sim.walltime
    d["num_nodes"] = sim.num_nodes

    return json.dumps(d), 200


@app.route("/SM/refresh/<simulation_id>", methods=["POST"])
@pny.db_session
def refresh_sim_state(simulation_id):
    sim=Simulation[simulation_id]
    if (sim is not None):        
        if sim.status=="PENDING" or sim.status=="CREATED" or sim.status=="QUEUED" or sim.status=="RUNNING" or sim.status=="ENDING":
            if sim.status!="CREATED":
                handleRefreshOfSimulations([sim])
            return "Status refreshed", 200
        else:
            return "Simulation state is invalid for refresh operation", 401
    else:
        return "Simulation not found with that identifier", 404

@app.route("/SM/simulation/<simulation_id>", methods=["DELETE"])
@pny.db_session
def cancel_simulation(simulation_id):
    sim=Simulation[simulation_id]
    if (sim is not None):
        if (sim.status=="PENDING" or sim.status=="QUEUED" or sim.status=="RUNNING" or sim.status=="ENDING"):
            asyncio.run(delete_simulation_job(sim.machine.machine_name, sim.jobID))
        sim.status="CANCELLED"
        sim.status_updated=datetime.datetime.now()
        pny.commit()
        logger.Log("Cancelled simulation '"+simulation_id+"'", "system", sim.incident.uuid)
        return "Simulation deleted", 200
    else:
        return "Simulation not found with that identifier", 404

async def delete_simulation_job(machine_name, queue_id):        
    client = await Client.create(machine_name)
    await client.cancelJob(queue_id)

@app.route("/SM/submit", methods=["POST"])
@pny.db_session
def submit_job():
    data = request.get_json()

    simulation_uuid = data["simulation_uuid"]
    simulation = Simulation[simulation_uuid]
    if simulation.status == "CREATED":
        submission_data=asyncio.run(submit_job_to_machine(simulation.machine.machine_name, simulation.num_nodes, simulation.requested_walltime, simulation.directory, simulation.executable))
        if (submission_data[0]):
            simulation.jobID=submission_data[1]
            simulation.status="QUEUED"
            simulation.status_updated=datetime.datetime.now()
            logger.Log("Submitted simulation '"+simulation_uuid+"'", "system", simulation.incident.uuid)
            return "Job submitted", 200
        else:
            simulation.status="ERROR"
            simulation.status_message=submission_data[1]
            simulation.status_updated=datetime.datetime.now()
            logger.Log("Error submitting simulation '"+simulation_uuid+"' message is "+simulation.status_message, "system", simulation.incident.uuid, type=log.LogType.Error)
            return submission_data[1], 400
    else:
        return "Simulation can only be submitted when in created state", 400

async def submit_job_to_machine(machine_name, num_nodes, requested_walltime, directory, executable):        
    client = await Client.create(machine_name)
    queue_id = await client.submitJob(num_nodes, requested_walltime, directory, executable)
    return queue_id    

@app.route("/SM/create", methods=["POST"])
@pny.db_session
def create_job():    
    data = request.get_json()

    uuid=str(uuid4())
    incident_id = data["incident_id"]    
    num_nodes = data["num_nodes"]
    kind = data["kind"]
    requested_walltime = data["requested_walltime"]
    executable = data["executable"]

    incident_dir_id=incident_id.split("-")[-1]
    simulation_dir_id=uuid.split("-")[-1]

    if "directory" in data:
        directory = data["directory"]
    else:
        directory = "incident-"+incident_dir_id+"/simulation-"+simulation_dir_id

    if "template_dir" in data:
        template_dir = data["template_dir"]
    else:
        template_dir = ""

    try:                
        matched_machine_id=matchBestMachine(requested_walltime, num_nodes)   
        stored_machine=Machine.get(machine_id=matched_machine_id)        
        asyncio.run(create_job_on_machine(stored_machine.machine_name, directory, template_dir))        
        job_status="CREATED"
        logger.Log("Created simulation '"+uuid+"'", "system", incident_id)
    except MachineStatusManagerException as err:        
        job_status="ERROR"
        status_message="Error allocating machine to job, "+err.message
        stored_machine=None
        logger.Log("Error creating simulation, message is "+err.message, "system", incident_id, type=log.LogType.Error)
        return "Error allocating job to machine", 400
    except asyncio.exceptions.TimeoutError:
        return "Timeout contating remote machine", 504
    
    #fetch incident, make sure it exists
    try:
        incident = Incident[incident_id]
    except pny.core.ObjectNotFound:
        return "Invalid IncidentID", 500
    
    #create simulation in the DB
    simulation = Simulation(uuid=uuid, incident=incident, kind=kind, date_created=datetime.datetime.now(), num_nodes=num_nodes, 
                    requested_walltime=requested_walltime, executable=executable, status=job_status, status_updated=datetime.datetime.now(), directory=directory)
    if (job_status=="ERROR"):
        simulation.status_message=status_message
    if (stored_machine is not None):
        simulation.machine=stored_machine
    if ("queuestate_calls" in data):
        for key, value in data["queuestate_calls"].items():
            simulation.queue_state_calls.create(queue_state=key, call_name=value)  
    
    return jsonify({"simulation_id": uuid}), 201

async def create_job_on_machine(machine_name, directory, simulation_template_dir):        
    client = await asyncio.wait_for(Client.create(machine_name),timeout=3.0)
    mk_directory=await asyncio.wait_for(client.mkdir(directory, "-p"),timeout=3.0)
    if (simulation_template_dir != ""):    
        copy_template_submission = await asyncio.wait_for(client.cp(simulation_template_dir+"/*", directory, "-R"),timeout=3.0)    

@pny.db_session
def poll_outstanding_sim_statuses():
    simulations=pny.select(g for g in Simulation if g.status == "QUEUED" or g.status == "RUNNING" or g.status == "ENDING")
    handleRefreshOfSimulations(simulations)    

@pny.db_session
def handleRefreshOfSimulations(simulations):
    machine_to_queueid={}    
    queueid_to_sim={}
    workflow_stages_to_run=[]
    for sim in simulations:
        queueid_to_sim[sim.jobID]=sim
        if (not sim.machine.machine_name in machine_to_queueid):
            machine_to_queueid[sim.machine.machine_name]=[]
        machine_to_queueid[sim.machine.machine_name].append(sim.jobID)
    for key, value in machine_to_queueid.items():
        job_statuses=asyncio.run(get_job_status_update(key, value))
        for jkey, jvalue in job_statuses.items():
            queueid_to_sim[jkey].status_updated=datetime.datetime.now() 
            if (jvalue[0] != queueid_to_sim[jkey].status):
                logger.Log("Simulation '"+queueid_to_sim[jkey].uuid+"' changed state from '"+queueid_to_sim[jkey].status+"' to '"+jvalue[0]+"'", "system", queueid_to_sim[jkey].incident.uuid)
                queueid_to_sim[jkey].status=jvalue[0]
                if (len(jvalue[1]) > 0):
                    queueid_to_sim[jkey].walltime=jvalue[1]
                pny.commit()
                targetStateCall=checkMatchAgainstQueueStateCalls(queueid_to_sim[jkey].queue_state_calls, jvalue[0])
                if (targetStateCall is not None):                      
                    new_wf_stage_call={'targetName' : targetStateCall, 'incidentId' : queueid_to_sim[jkey].incident.uuid, 'simulationId' : queueid_to_sim[jkey].uuid, 'status' : jvalue[0]}
                    workflow_stages_to_run.append(new_wf_stage_call)
    pny.commit()
    if workflow_stages_to_run:
        issueWorkFlowStageCalls(workflow_stages_to_run)

def issueWorkFlowStageCalls(workflow_stages_to_run):
    workflow.OpenConnection()
    for wf_call in workflow_stages_to_run:            
        msg={}    
        msg["IncidentID"] = wf_call["incidentId"]        
        msg["simulationId"]=wf_call["simulationId"]        

        origionatorPrettyStr=None
        if wf_call["status"] == "COMPLETED":
            origionatorPrettyStr="Simulation Completed"
            simulation = Simulation[wf_call["simulationId"]]
            directory_listing = asyncio.run(get_job_directory_listing(simulation.machine.machine_name, simulation.directory))
            msg["directoryListing"]=directory_listing
        elif wf_call["status"] == "QUEUED":
            origionatorPrettyStr="Simulation Queued"
        elif wf_call["status"] == "RUNNING":
            origionatorPrettyStr="Simulation Running"
        elif wf_call["status"] == "ENDING":
            origionatorPrettyStr="Simulation Ending"
        elif wf_call["status"] == "HELD":
            origionatorPrettyStr="Simulation Held"
        workflow.send(message=msg, queue=wf_call["targetName"], providedCaller=origionatorPrettyStr)

    workflow.FlushMessages()
    workflow.CloseConnection()

async def get_job_directory_listing(machine_name, directory_name):        
    client = await Client.create(machine_name)
    return await client.ls(directory_name)    

def checkMatchAgainstQueueStateCalls(state_calls, queue_state):
    for state_call in state_calls:
        if (queue_state == state_call.queue_state):
            return state_call.call_name
    return None

async def get_job_status_update(machine_name, queue_ids):        
    client = await Client.create(machine_name)
    status= await client.getJobStatus(queue_ids)
    return status

if __name__ == "__main__":
    initialiseDatabase()
    poll_scheduler.start()
    runon = datetime.datetime.now()+ datetime.timedelta(seconds=30)
    poll_scheduler.add_job(poll_outstanding_sim_statuses, 'interval', seconds=60, next_run_time = runon)
    app.run(host="0.0.0.0", port=5500)
    poll_scheduler.shutdown()
