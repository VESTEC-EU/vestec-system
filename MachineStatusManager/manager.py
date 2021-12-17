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
from Database.workflow import Simulation
from DataManager.client import predictDatasetTransferPerformance, DataManagerException
import datetime
from uuid import uuid4
import Utils.log as log
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from models.current_machine_state_queue_model import QueuePredictionCurrentMachineState
from mproxy.client import Client
import asyncio
import aio_pika
from dateutil.parser import parse

poll_scheduler=BackgroundScheduler(executors={"default": ThreadPoolExecutor(1)})

app = Flask("Machine Status Manager")
logger = log.VestecLogger("Machine Status Manager")

predictors={"cirrus": QueuePredictionCurrentMachineState("cirrus")}
detailed_machines_status={}

@pny.db_session
def _check_queue_predictors():
    machines=pny.select(machine for machine in Machine)
    for machine in machines:
        if machine.machine_name not in predictors and machine.enabled:
            predictors[machine.machine_name]=QueuePredictionCurrentMachineState(machine.machine_name)

@app.route("/MSM/health", methods=["GET"])
def get_health():
    return jsonify({"status": 200}), 200

@app.route("/MSM/machine/<machine_id>", methods=["DELETE"])
@pny.db_session
def delete_machine(machine_id):
    stored_machine=Machine.get(machine_id=machine_id)
    if (stored_machine is not None):        
        stored_machine.delete()        
        return jsonify({"msg": "Machine deleted"}), 200
    else:
        return jsonify({"msg":"No matching machine"}), 404

@app.route("/MSM/enable/<machine_id>", methods=["POST"])
@pny.db_session
def enable_machine(machine_id):
    stored_machine=Machine.get(machine_id=machine_id)
    if (stored_machine is not None):        
        stored_machine.enabled=True        
        return jsonify({"msg": "Machine enabled"}), 200
    else:
        return jsonify({"msg":"No matching machine"}), 404

@app.route("/MSM/disable/<machine_id>", methods=["POST"])
@pny.db_session
def disable_machine(machine_id):
    stored_machine=Machine.get(machine_id=machine_id)
    if (stored_machine is not None):        
        stored_machine.enabled=False        
        return jsonify({"msg": "Machine disabled"}), 200
    else:
        return jsonify({"msg":"No matching machine"}), 404

@app.route("/MSM/enable_testmode/<machine_id>", methods=["POST"])
@pny.db_session
def enable_testmode_machine(machine_id):
    stored_machine=Machine.get(machine_id=machine_id)
    if (stored_machine is not None):        
        stored_machine.test_mode=True        
        return jsonify({"msg": "Enabled test mode on machine"}), 200
    else:
        return jsonify({"msg":"No matching machine"}), 404

@app.route("/MSM/disable_testmode/<machine_id>", methods=["POST"])
@pny.db_session
def disable_testmode_machine(machine_id):
    stored_machine=Machine.get(machine_id=machine_id)
    if (stored_machine is not None):        
        stored_machine.test_mode=False        
        return jsonify({"msg": "Disabled test mode on machine"}), 200
    else:
        return jsonify({"msg":"No matching machine"}), 404

@app.route("/MSM/add", methods=["POST"])
@pny.db_session
def add_machine():
    machine_info = request.json    
    machine_name=machine_info.get("machine_name", None)
    host_name=machine_info.get("host_name", None)
    scheduler=machine_info.get("scheduler", None)
    connection_type=machine_info.get("connection_type", None)
    num_nodes=machine_info.get("num_nodes", None)
    cores_per_node=machine_info.get("cores_per_node", None)
    base_work_dir=machine_info.get("base_work_dir", None)

    newMachine = Machine(machine_id=str(uuid4()), machine_name=machine_name, host_name=host_name, scheduler=scheduler, connection_type=connection_type, num_nodes=num_nodes, cores_per_node=cores_per_node, base_work_dir=base_work_dir)
    pny.commit()
    return jsonify({"msg": "Machine added"}), 201

def _isFloat(value):
  try:
    float(value)
    return True
  except ValueError:
    return False

@pny.db_session
def _getPredictedRuntime(executable, machine, requested_walltime):
    previous_executables=pny.select(sim for sim in Simulation if sim.executable == executable and sim.machine == machine)[:]
    avg_exec_time=0.0
    tot_count=0
    for exec in previous_executables:        
        if exec.machine_run_time != "" and _isFloat(exec.machine_run_time):
            avg_exec_time+=float(exec.machine_run_time)
            tot_count+=1
    if (tot_count > 0):
        return avg_exec_time/tot_count
    else:
        pt=parse(requested_walltime)
        return pt.second + pt.minute*60 + pt.hour*3600

def _getPredictedDataTransferTime(machine_name, associated_datasets):
    data_transfer_time=0.0
    for data_set in associated_datasets:
        try:
            data_transfer_time+=predictDatasetTransferPerformance(data_set, machine_name)
        except DataManagerException as err:
            pass
    print(data_transfer_time)
    return data_transfer_time

@pny.db_session
def _getPredictedTotalTime(requested_walltime, requested_num_nodes, executable, machine, associated_datasets):
    return 60
    #queue_time=predictors[machine.machine_name].predict(requested_walltime, requested_num_nodes, detailed_machines_status[machine.machine_name])    
    #return queue_time + _getPredictedRuntime(executable, machine, requested_walltime) + _getPredictedDataTransferTime(machine.machine_name, associated_datasets)

@app.route("/MSM/matchmachine", methods=["POST"])
@pny.db_session
def get_appropriate_machine():
    _check_queue_predictors()
    data = request.get_json()
    requested_walltime = data["walltime"]
    requested_num_nodes = data["num_nodes"]
    executable=data["executable"]
    number_retrieve=data["number_retrieve"]
    associated_datasets=data["associated_datasets"]
    machines=pny.select(machine for machine in Machine)
    predicted_total_times={}
    for machine in machines:
        if machine.enabled:
            if machine.machine_name not in detailed_machines_status:
                poll_machine_statuses()
            predicted_total_times[machine]=_getPredictedTotalTime(requested_walltime, requested_num_nodes, executable, machine, associated_datasets)            
    if predicted_total_times:
        sorted_times={k: v for k, v in sorted(predicted_total_times.items(), key=lambda item: item[1])}
        sorted_machines=list(sorted_times.keys())
        mids=[]
        for i in range(number_retrieve):
            mids.append(sorted_machines[i].machine_id)
        return jsonify({"machine_ids": mids}), 200
    else:
        return jsonify({"msg":"No matching machine"}), 404

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
            machine_info["connection_type"]=machine.connection_type
            machine_info["nodes"]=machine.num_nodes            
            machine_info["cores_per_node"]=machine.cores_per_node
            machine_info["enabled"]=machine.enabled
            machine_info["test_mode"]=machine.test_mode
            if (machine.status is not None):
                machine_info["status"]=machine.status
            if (machine.status_last_checked is not None):
                machine_info["status_last_checked"]=machine.status_last_checked.strftime("%d/%m/%Y, %H:%M:%S")
            machine_descriptions.append(machine_info)         
    
    return json.dumps(machine_descriptions), 200

@pny.db_session
def poll_machine_statuses():
    machines=pny.select(machine for machine in Machine)
    for machine in machines:
        if not machine == None and machine.enabled: 
            status,detailed_status=asyncio.run(retrieve_machine_status(machine.machine_name))
            detailed_machines_status[machine.machine_name]=detailed_status
            machine.status=status
            machine.status_last_checked=datetime.datetime.now()
            pny.commit()            

async def retrieve_machine_status(machine_name):        
    client = await Client.create(machine_name)
    status = await client.getstatus()
    detailed_status = await client.getDetailedStatus()
    return status, detailed_status
            
if __name__ == "__main__":
    initialiseDatabase()
    _check_queue_predictors()
    poll_scheduler.start()
    runon = datetime.datetime.now()+ datetime.timedelta(seconds=300)
    poll_scheduler.add_job(poll_machine_statuses, 'interval', seconds=1200, next_run_time = runon) # Machine queue update every 20 minutes
    app.run(host="0.0.0.0", port=5502)    
    poll_scheduler.shutdown()
