import manager.workflow as workflow
import SimulationManager.client as client
import requests
import time
import os
import json

from .utils import logfile, logTest


@workflow.handler
def sm_tests_init(msg):
    incident = msg["IncidentID"]
    logdir = msg["logdir"]

    with logfile(logdir) as f:
        f.write("Simulation Manager tests\n")
    
    workflow.send(msg,"sm_tests_create")


@workflow.handler
def sm_tests_complete(msg):
    incident = msg["IncidentID"]
    logdir = msg["logdir"]

    workflow.send(msg,"run_tests")


@workflow.handler
def sm_tests_create(msg):
    incident = msg["IncidentID"]
    logdir = msg["logdir"]

    msg["simulations"] = []

    

    try:
        uuid=client.createSimulation(incident_id=incident,
                                num_nodes = 1,
                                requested_walltime="0:0:1",
                                kind = "test bjob",
                                executable = "subtest.sh",
                                template_dir="templates",
                                queuestate_callbacks= {
                                    "RUNNING": "sm_tests_check",
                                    "COMPLETED": "sm_tests_check",
                                })
    except client.SimulationManagerException as e:
        logTest("sm_create","FAIL",logdir,e.message)
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
        cleanup(msg)
        return

    logTest("sm_create","PASS",logdir)
    msg["total_tests"]+=1
    msg["passed_tests"]+=1

    msg["simulations"].append(uuid)

    workflow.send(msg,"sm_tests_info")


@workflow.handler
def sm_tests_info(msg):
    incident = msg["IncidentID"]
    logdir = msg["logdir"]

    sim_id = msg["simulations"][0]

    try:
        info = client.getSimulationInfo(sim_id)
    except client.SimulationManagerException as e:
        logTest("sm_info","FAIL",logdir,e.message)
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
        cleanup(msg)
        return
    
    if info["IncidentID"] != incident:
        logTest("sm_info","FAIL",logdir,"Incident for simulation is not correct")
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
        cleanup(msg)
        return

    logTest("sm_info","PASS",logdir)
    msg["total_tests"]+=1
    msg["passed_tests"]+=1

    workflow.send(msg,"sm_tests_submit")




@workflow.handler
def sm_tests_submit(msg):
    incident = msg["IncidentID"]
    logdir = msg["logdir"]

    sim_id = msg["simulations"][0]

    try:
        client.submitSimulation(sim_id)
    except client.SimulationManagerException as e:
        logTest("sm_submit","FAIL",logdir,e.message)
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
        cleanup(msg)
        return

    logTest("sm_submit","PASS",logdir)
    msg["total_tests"]+=1
    msg["passed_tests"]+=1
    
    workflow.send(msg,"sm_tests_check")



    

#refreshes the simulation status (if in test mode this should also move the status on one point)
@workflow.handler
def sm_tests_refresh(msg):
    print('sm_tests_refresh', msg)
    sim_id = msg["simulations"][0]

    try:
        client.refreshSimilation(sim_id)
    except client.SimulationManagerException as e:
        print('sm_tests_refresh',e)
        try:
            info = client.getSimulationInfo(sim_id)
            print('sm_tests_refresh getsimulationinfo', info)
        except client.SimulationManagerException as e2:
            logTest("sm_refresh","FAIL",logdir,e.message)
            msg["total_tests"]+=1
            msg["failed_tests"]+=1
            cleanup(msg)
            return
        if info["status"] != "COMPLETE" or info["status"] != "CANCELLED":
            print('sm_tests_refresh getsimulationinfo fail', e.message)
            logTest("sm_refresh","FAIL",logdir,e.message)
            msg["total_tests"]+=1
            msg["failed_tests"]+=1
            cleanup(msg)
            return



@workflow.atomic    
@workflow.handler
def sm_tests_check(msg):
    incident = msg["IncidentID"]

    
    if msg["originator"] == "sm_tests_submit":
        workflow.Persist.Put(incident,msg)
        print('force change state')

        #if in test mode this will force the simulation to change state, triggering a new message
        workflow.send(msg,"sm_tests_refresh")
        return
    
    elif msg["originator"] == "Simulation Running":
        #get the first persisted message - should be from sm_test_submit
        #msg = workflow.Persist.Get(incident)[0]
        msg = workflow.Persist.Get(incident)
        print('sim running', len(msg), msg)
        msg = msg[0]
        logdir = msg["logdir"]

        logTest("sm_running","PASS",logdir)
        msg["total_tests"]+=1
        msg["passed_tests"]+=1

        workflow.Persist.Put(incident,msg)
        
        #if in test mode this will force the simulation to change state, triggering a new message
        workflow.send(msg,"sm_tests_refresh")
        return
    
    elif msg["originator"] == "Simulation Completed":
        #get the latest persisted message - should be [1]
        #msg = workflow.Persist.Get(incident)[1]
        msg = workflow.Persist.Get(incident)
        print('sim complete', len(msg), msg)
        msg = msg[1]
        logdir = msg["logdir"]

        logTest("sm_completed","PASS",logdir)
        msg["total_tests"]+=1
        msg["passed_tests"]+=1

        workflow.send(msg,"sm_tests_cancel")
        return
    else:
        logTest("sm_check","FAIL",logdir,"Message came from unexpected originator")
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
        cleanup(msg)


@workflow.handler
def sm_tests_cancel(msg):
    incident = msg["IncidentID"]
    logdir = msg["logdir"]

    sim_id = msg["simulations"][0]

    try:
        client.cancelSimulation(sim_id)

        info = client.getSimulationInfo(sim_id)
        if info["status"] != "CANCELLED":
            logTest("sm_cancel","FAIL",logdir,"Simulation status is not cancelled")
            msg["total_tests"]+=1
            msg["failed_tests"]+=1
            cleanup(msg)
            return
    except client.SimulationManagerException as e:
        logTest("sm_refresh","FAIL",logdir,e.message)
        msg["total_tests"]+=1
        msg["failed_tests"]+=1
        cleanup(msg)
        return
    
    logTest("sm_submit","PASS",logdir)
    msg["total_tests"]+=1
    msg["passed_tests"]+=1

    workflow.send(msg,"sm_tests_complete")









    

#attempts to deregister any endpoints associated with this incident and requests the tests are aborted
def cleanup(msg):
    incident = msg["IncidentID"]
    
    workflow.send(queue="abort_tests",message=msg)
    


def RegisterHandlers():
    workflow.RegisterHandler(handler=sm_tests_init,queue="sm_tests_init")
    workflow.RegisterHandler(handler=sm_tests_complete,queue="sm_tests_complete")
    workflow.RegisterHandler(handler=sm_tests_create,queue="sm_tests_create")
    workflow.RegisterHandler(handler=sm_tests_submit,queue="sm_tests_submit")
    workflow.RegisterHandler(handler=sm_tests_refresh,queue="sm_tests_refresh")
    workflow.RegisterHandler(handler=sm_tests_info,queue="sm_tests_info")
    workflow.RegisterHandler(handler=sm_tests_check,queue="sm_tests_check")
    workflow.RegisterHandler(handler=sm_tests_check,queue="sm_tests_check")
    workflow.RegisterHandler(handler=sm_tests_cancel,queue="sm_tests_cancel")
    
    
    
