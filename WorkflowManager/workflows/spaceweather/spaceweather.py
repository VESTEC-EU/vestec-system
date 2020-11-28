import sys
#sys.path.append("../")
from manager import workflow
import os
import pony.orm as pny
import datetime
import time
import json
from base64 import b64decode
from Database import LocalDataStorage
from Database.workflow import Simulation
from DataManager.client import registerDataWithDM, putByteDataViaDM, DataManagerException
from SimulationManager.client import createSimulation, submitSimulation, SimulationManagerException
from ExternalDataInterface.client import registerEndpoint, ExternalDataInterfaceException, removeEndpoint

# create and submit jobs
def launch_simulation(msg):
    print("\nSpaceweather simulation submit handler")
    IncidentID      = msg["IncidentID"]
    CaseName        = msg['SimulationCase']
    ParaViewAddress = msg['ParaViewAddress']
    ParaViewPort    = msg['ParaViewPort']
    print(msg)
    if CaseName is None:
        print('Case name is none!')
        return

    try:
        callbacks = { 'COMPLETED': 'spaceweather_postprocess' }
        sim_id = createSimulation(IncidentID,
                                  1,
                                  '00:10:00',
                                  CaseName,
                                  'run_spaceweather.sh %s %s %d' % (CaseName, ParaViewAddress, ParaViewPort),
                                  callbacks,
                                  template_dir='template_'+CaseName)
        submitSimulation(sim_id)
    except SimulationManagerException as err:
        print("Error creating or submitting simulation "+err.message)
        return

@workflow.handler
def spaceweather_base_simulation(msg):
    print("\nSpaceweather base simulation")
    try:
        launch_simulation(msg)
    except e:
        print('Error launching base case '+e.message)

@workflow.handler
def spaceweather_GuideCase1_simulation(msg):
    print("\nSpaceweather GuideCase1 simulation")
    try:
        launch_simulation(msg)
    except e:
        print('Error launching GuideCase1 case '+e.message)

@workflow.handler
def spaceweather_GuideCase2_simulation(msg):
    print("\nSpaceweather GuideCase2 simulation")
    try:
        launch_simulation(msg)
    except e:
        print('Error launching base case '+e.message)
 
# space weather init
@workflow.handler
def spaceweather_init(msg):
    print("\nSpaceweather simulation init handler")
    IncidentID = msg["IncidentID"]

    #workflow.setIncidentActive(IncidentID)

    msg['SimulationCase']  = '2Dxy'
    msg['ParaViewAddress'] = 'localhost'
    msg['ParaViewPort']    = 22222
    workflow.send(queue="spaceweather_base_simulation", message=msg)

    msg['SimulationCase'] = '2DxyGuideCase1'
    msg['ParaViewAddress'] = 'localhost'
    msg['ParaViewPort']    = 22223
    workflow.send(queue="spaceweather_GuideCase1_simulation", message=msg)

    msg['SimulationCase'] = '2DxyGuideCase2'
    msg['ParaViewAddress'] = 'localhost'
    msg['ParaViewPort']    = 22224
    workflow.send(queue="spaceweather_GuideCase2_simulation", message=msg)

# space weather shutdown
@workflow.handler
def spaceweather_postprocess(msg):
    print("\nSpaceweather simulation postprocess handler")
    IncidentID = msg["IncidentID"]
    CaseName   = msg['originator']

    workflow.Persist.Put(IncidentID, {'type': 'postprocessed'})
    logs = workflow.Persist.Get(IncidentID)
    print(logs)

    completed = 0
    if len(logs) >= 3:
        for log in logs:
            if 'type' in log or log['type'] == 'postprocessed':
                completed = completed + 1

    if completed >= 3:
        print('All simulation completed')
        workflow.send(queue='spaceweather_shutdown', message=msg)

    #workflow.Persist.Put(IncidentID, {"type": "postprocssed", "originator": CaseName})
    #logs = workflow.Persist.Get(IncidentID)
    #print(logs)

    #_2Dxy           = False
    #_2DxyGuideCase1 = False
    #_2DxyGuideCase2 = False

    #for log in logs:
    #    if "type" in log and log["processed"] == "shutdown":
    #        if log["originator"] == "spaceweather_base_simulation"      : _2Dxy=True
    #        if log["originator"] == "spaceweather_GuideCase1_simulation": _2DxyGuideCase1=True
    #        if log["originator"] == "spaceweather_GuideCase2_simulation": _2DxyGuideCase2=True

    #if _2Dxy is True and _2DxyGuideCase1 is True and _2DxyGuideCase2 is True:
    #    print('Complete incident', IncidentID)
    #    workflow.send(queue="spaceweather_shutdown", message=msg)

@workflow.handler
def spaceweather_shutdown(msg):
    print("\nSpaceweather simulation shutdown handler")
    IncidentID = msg["IncidentID"]
    workflow.Complete(IncidentID)

# we have to register them with the workflow system
def RegisterHandles():
    workflow.RegisterHandler(spaceweather_base_simulation,       "spaceweather_base_simulation")
    workflow.RegisterHandler(spaceweather_GuideCase1_simulation, "spaceweather_GuideCase1_simulation")
    workflow.RegisterHandler(spaceweather_GuideCase2_simulation, "spaceweather_GuideCase2_simulation")
    workflow.RegisterHandler(spaceweather_init,                  "spaceweather_init")
    workflow.RegisterHandler(spaceweather_postprocess,           "spaceweather_postprocess")
    workflow.RegisterHandler(spaceweather_shutdown,              "spaceweather_shutdown")
