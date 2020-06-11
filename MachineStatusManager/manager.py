from __future__ import print_function
import sys
sys.path.append("../")
from flask import Flask, request, jsonify
import threading
import time
import json
import pony.orm as pny
from Database import initialiseDatabase
from Database.machine import Machine
import datetime
from uuid import uuid4
import ConnectionManager
import Templating
import Utils.log as log

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
                machine_info["status_last_checked"]=machine.status_last_checked
            machine_descriptions.append(machine_info)         
    
    return json.dumps(machine_descriptions)

if __name__ == "__main__":
    initialiseDatabase()    
    app.run(host="0.0.0.0", port=5502)
