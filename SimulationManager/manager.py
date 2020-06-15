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
from Database.workflow import RegisteredWorkflow, Simulation
import datetime
from uuid import uuid4
import Utils.log as log
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor

from mproxy.client import Client
import asyncio
import aio_pika

MSM_URL= 'http://127.0.0.1:5502/MSM'

poll_scheduler=BackgroundScheduler(executors={"default": ThreadPoolExecutor(1)})

app = Flask("Simulation Manager")
logger = log.VestecLogger("Simulation Manager")

@app.route("/SM/health", methods=["GET"])
def get_health():
    return jsonify({"status": 200})

@app.route("/SM/simulation/<simulation_id>", methods=["DELETE"])
@pny.db_session
def cancel_simulation(simulation_id):
    sim=Simulation[simulation_id]
    if (sim is not None):
        asyncio.run(delete_simulation_job(sim.machine.machine_name, sim.jobID))
        sim.status="CANCELLED"
        sim.status_updated=datetime.datetime.now()
        pny.commit()
        return jsonify({"status": 201})
    else:
        return jsonify({"status": 401})

async def delete_simulation_job(machine_name, queue_id):    
    connection = await aio_pika.connect(host="localhost")
    client = await Client.create(machine_name, connection)
    await client.cancelJob(queue_id)    

@app.route("/SM/create", methods=["POST"])
@pny.db_session
def create_job():    
    data = request.get_json()

    uuid=str(uuid4())
    incident_id = data["incident_id"]    
    num_nodes = data["num_nodes"]
    requested_walltime = data["requested_walltime"]
    executable = data["executable"]    

    simulation = Simulation(uuid=uuid, incident=incident_id, date_created=datetime.datetime.now(), num_nodes=num_nodes, requested_walltime=requested_walltime, executable=executable, status_updated=datetime.datetime.now())
    pny.commit()

    matched_machine=requests.get(MSM_URL + '/matchmachine?walltime='+str(requested_walltime)+'&num_nodes='+str(num_nodes))
    stored_machine=Machine.get(machine_id=matched_machine.json()["machine_id"])

    simulation.machine=stored_machine
    simulation.status="QUEUED"
    simulation.status_updated=datetime.datetime.now()
    simulation.jobID=asyncio.run(submit_job_to_machine(stored_machine.machine_name, num_nodes, requested_walltime, executable))

    pny.commit()
    return jsonify({"status": 201, "simulation_id": uuid})

async def submit_job_to_machine(machine_name, num_nodes, requested_walltime, executable):    
    connection = await aio_pika.connect(host="localhost")
    client = await Client.create(machine_name, connection)
    queue_id = await client.submitJob(num_nodes, requested_walltime, executable)
    return queue_id

@pny.db_session
def poll_outstanding_sim_statuses():
    simulations=pny.select(g for g in Simulation if g.status == "QUEUED" or g.status == "RUNNING")
    machine_to_queueid={}    
    queueid_to_sim={}
    for sim in simulations:
        queueid_to_sim[sim.jobID]=sim
        if (not sim.machine.machine_name in machine_to_queueid):
            machine_to_queueid[sim.machine.machine_name]=[]
        machine_to_queueid[sim.machine.machine_name].append(sim.jobID)
    for key, value in machine_to_queueid.items():
        job_statuses=asyncio.run(get_job_status_update(key, value))
        for jkey, jvalue in job_statuses.items():
            if (jvalue != queueid_to_sim[jkey].status):
                queueid_to_sim[jkey].status=jvalue
                queueid_to_sim[jkey].status_updated=datetime.datetime.now()

async def get_job_status_update(machine_name, queue_ids):    
    connection = await aio_pika.connect(host="localhost")
    client = await Client.create(machine_name, connection)
    status= await client.getJobStatus(queue_ids)
    return status

if __name__ == "__main__":
    initialiseDatabase()
    poll_scheduler.start()
    runon = datetime.datetime.now()+ datetime.timedelta(seconds=5)
    poll_scheduler.add_job(poll_outstanding_sim_statuses, 'interval', seconds=10, next_run_time = runon)
    app.run(host="0.0.0.0", port=5505)
    poll_scheduler.shutdown()
