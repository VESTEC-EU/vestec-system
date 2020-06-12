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

from mproxy.client import Client
import asyncio
import aio_pika

MSM_URL= 'http://127.0.0.1:5502/MSM'

app = Flask("Simulation Manager")
logger = log.VestecLogger("Simulation Manager")

@app.route("/SM/health", methods=["GET"])
def get_health():
    return jsonify({"status": 200})

@app.route("/SM/status/<simulation_id>", methods=["GET"])
@pny.db_session
def retrieve_simulation_status(simulation_id):
    pass

@app.route("/SM/create", methods=["POST"])
@pny.db_session
def create_job():    
    data = request.get_json()

    uuid=str(uuid4())
    incident_id = data["incident_id"]    
    num_nodes = data["num_nodes"]
    requested_walltime = data["requested_walltime"]
    executable = data["executable"]    

    simulation = Simulation(uuid=uuid, incident=incident_id, date_created=datetime.datetime.now(), num_nodes=num_nodes, requested_walltime=requested_walltime, executable=executable)
    pny.commit()

    matched_machine=requests.get(MSM_URL + '/matchmachine?walltime='+str(requested_walltime)+'&num_nodes='+str(num_nodes))
    stored_machine=Machine.get(machine_id=matched_machine.json()["machine_id"])

    simulation.machine=stored_machine
    simulation.status="QUEUED"
    simulation.jobID=asyncio.run(submit_job_to_machine(stored_machine.machine_name, num_nodes, requested_walltime, executable))

    pny.commit()
    return jsonify({"status": 201, "simulation_id": uuid})

async def submit_job_to_machine(machine_name, num_nodes, requested_walltime, executable):    
    connection = await aio_pika.connect(host="localhost")
    client = await Client.create(machine_name, connection)
    queue_id = await client.submitJob(num_nodes, requested_walltime, executable)
    return queue_id

if __name__ == "__main__":
    initialiseDatabase()    
    app.run(host="0.0.0.0", port=5505)
