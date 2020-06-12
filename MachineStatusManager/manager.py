from __future__ import print_function
import sys
sys.path.append("../")
sys.path.append("../MachineInterface")
from flask import Flask, request, jsonify
import threading
import time
import json
import pony.orm as pny
import requests
from Database import initialiseDatabase
from Database.machine import Machine
import datetime
from uuid import uuid4
import ConnectionManager
import Templating
import Utils.log as log
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor

from mproxy.client import Client
import asyncio
import aio_pika

poll_scheduler=BackgroundScheduler(executors={"default": ThreadPoolExecutor(1)})

app = Flask("Machine Status Manager")
logger = log.VestecLogger("Machine Status Manager")

@app.route("/MSM/health", methods=["GET"])
def get_health():
    return jsonify({"status": 200})

@app.route("/MSM/enable/<machine_id>", methods=["POST"])
@pny.db_session
def enable_machine(machine_id):
    stored_machine=Machine.get(machine_id=machine_id)
    if (stored_machine is not None):        
        stored_machine.enabled=True
        pny.commit()
    return jsonify({"status": 200})

@app.route("/MSM/disable/<machine_id>", methods=["POST"])
@pny.db_session
def disable_machine(machine_id):
    stored_machine=Machine.get(machine_id=machine_id)
    if (stored_machine is not None):        
        stored_machine.enabled=False
        pny.commit()
    return jsonify({"status": 200})

@app.route("/MSM/add", methods=["POST"])
@pny.db_session
def add_machine():
    machine_info = request.json    
    machine_name=machine_info.get("machine_name", None)
    host_name=machine_info.get("host_name", None)
    scheduler=machine_info.get("scheduler", None)
    num_nodes=machine_info.get("num_nodes", None)
    cores_per_node=machine_info.get("cores_per_node", None)
    base_work_dir=machine_info.get("base_work_dir", None)

    newMachine = Machine(machine_id=str(uuid4()), machine_name=machine_name, host_name=host_name, scheduler=scheduler, num_nodes=num_nodes, cores_per_node=cores_per_node, base_work_dir=base_work_dir)
    pny.commit()
    return jsonify({"status": 200})

@app.route("/MSM/matchmachine", methods=["GET"])
@pny.db_session
def get_appropriate_machine():
    requested_walltime = request.args.get("walltime", None)
    requested_num_nodes = request.args.get("num_nodes", None)
    stored_machine=Machine.get(machine_name="test")
    return jsonify({"status": 200, "machine_id":stored_machine.machine_id})

@app.route("/MSM/machinestatuses", methods=["GET"])
@pny.db_session
def get_machine_status():    
    machine_descriptions=[]
    machines=pny.select(machine for machine in Machine)
    for machine in machines:
        if not machine == None:
            machine_info={}
            machine_info["uuid"]=machine.machine_id
            machine_info["name"]=machine.machine_name
            machine_info["host_name"]=machine.host_name
            machine_info["scheduler"]=machine.scheduler
            machine_info["nodes"]=machine.num_nodes            
            machine_info["cores_per_node"]=machine.cores_per_node
            machine_info["enabled"]=machine.enabled
            if (machine.status is not None):
                machine_info["status"]=machine.status
            if (machine.status_last_checked is not None):
                machine_info["status_last_checked"]=machine.status_last_checked.strftime("%d/%m/%Y, %H:%M:%S")
            machine_descriptions.append(machine_info)         
    
    return json.dumps(machine_descriptions)

@pny.db_session
def poll_machine_statuses():
    machines=pny.select(machine for machine in Machine)
    for machine in machines:
        if not machine == None and machine.enabled: 
            status=asyncio.run(retrieve_machine_status())
            machine.status=status
            machine.status_last_checked=datetime.datetime.now()
            pny.commit()

async def retrieve_machine_status():    
    connection = await aio_pika.connect(host="localhost")
    client = await Client.create("test", connection)
    status = await client.getstatus()
    return status
            
if __name__ == "__main__":
    initialiseDatabase()    
    poll_scheduler.start()
    runon = datetime.datetime.now()+ datetime.timedelta(seconds=5)
    poll_scheduler.add_job(poll_machine_statuses, 'interval', seconds=360, next_run_time = runon)
    app.run(host="0.0.0.0", port=5502)    
    poll_scheduler.shutdown()
