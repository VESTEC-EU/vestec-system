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
from Database.workflow import Simulation, Incident
#from DataManager.client import registerDataWithDM, putByteDataViaDM, DataManagerException
from DataManager.client import moveDataViaDM, DataManagerException, getInfoForDataInDM, putByteDataViaDM, registerDataWithDM, copyDataViaDM, getLocalFilePathPrepend
from SimulationManager.client import createSimulation, submitSimulation, SimulationManagerException
from ExternalDataInterface.client import registerEndpoint, ExternalDataInterfaceException, removeEndpoint

# create and submit jobs
def _launch_simulation(msg, callback='spaceweather_postprocess'):
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
        callbacks = { 'COMPLETED': callback }
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
    IncidentId = msg["IncidentID"]
    try:
        _launch_simulation(msg)
        workflow.send(queue="spaceweather_postprocess", message=msg) # dummy connection
    except e:
        print('Error launching base case '+e.message)

@workflow.handler
def spaceweather_GuideCase1_simulation(msg):
    print("\nSpaceweather GuideCase1 simulation")
    IncidentId = msg["IncidentID"]
    try:
        _launch_simulation(msg)
        workflow.send(queue="spaceweather_postprocess", message=msg) # dummy connection
    except e:
        print('Error launching GuideCase1 case '+e.message)

@workflow.handler
def spaceweather_GuideCase2_simulation(msg):
    print("\nSpaceweather GuideCase2 simulation")
    IncidentId = msg["IncidentID"]
    try:
        _launch_simulation(msg)
        workflow.send(queue="spaceweather_postprocess", message=msg) # dummy connection
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

    IncidentID = msg["IncidentID"]
    originator = msg['originator']
    logs = workflow.Persist.Get(IncidentID)
    print("\nSpaceweather simulation postprocess handler", IncidentID)

    if originator == 'Simulation Completed':
        simulationId = msg["simulationId"]
        simulationIdPostfix=simulationId.split("-")[-1]
        directoryListing=msg["directoryListing"]

        print("\nResults available for wildfire analyst simulation!") 

        with pny.db_session:
            myincident = Incident[IncidentID]
            simulation=Simulation[simulationId]
            machine_name=simulation.machine.machine_name
            machine_basedir=simulation.machine.base_work_dir
            if machine_basedir[-1] != "/": machine_basedir+="/"

        if simulation is not None:
            result_files={}
            for entry in directoryListing:
                # '193993425     96 -rw-rw-r--   1 vestec   vestec      97574 Nov 28 15:48 incident-bb97271000f5/simulation-a350bba3ee36/output_log.txt'
                tokens=entry.split()
                if len(tokens) == 11 and "data" in tokens[-1]:
                    result_files[tokens[-1]]=int(tokens[6])

            data_uuids = []
            for filepath, filesize in result_files.items():
                filename  = os.path.basename(filepath)
                directory = os.path.dirname(filepath)
                print(filename, directory, filesize)

                # register output data with data manager
                try:
                    #if ".vtu" in filename:
                    #    data_uuid=registerDataWithDM(filename.replace('(', r'\(').replace(')', r'\)'), machine_name, "spaceweahter simulation ("+simulation.kind+")",
                    #                                 "application/xml", filesize, "vtu", path=directory, associate_with_incident=True, incidentId=IncidentID,
                    #                                 kind=simulation.kind, comment="Basecase created by iPICmini on "+machine_name)
                    if ".ttk" in filename:
                        data_uuid=registerDataWithDM(filename.replace('(', r'\(').replace(')', r'\)'), machine_name, "spaceweahter simulation ("+simulation.kind+")",
                                                     "application/octet-stream", filesize, "ttk", path=directory, associate_with_incident=True, incidentId=IncidentID,
                                                     kind=simulation.kind, comment="Basecase created by iPICmini on "+machine_name)
                        data_uuids.append(data_uuid)
                    elif ".csv" in filename:
                        data_uuid=registerDataWithDM(filename.replace('(', r'\(').replace(')', r'\)'), machine_name, "spaceweahter simulation ("+simulation.kind+")",
                                                     "text/csv", filesize, "csv", path=directory, associate_with_incident=True, incidentId=IncidentID,
                                                     kind=simulation.kind, comment="Basecase created by iPICmini on "+machine_name)
                        data_uuids.append(data_uuid)
                    elif ".vtk" in filename:
                        data_uuid=registerDataWithDM(filename.replace('(', r'\(').replace(')', r'\)'), machine_name, "spaceweahter simulation ("+simulation.kind+")",
                                                     "application/octet-stream", filesize, "vtk", path=directory, associate_with_incident=True, incidentId=IncidentID,
                                                     kind=simulation.kind, comment="Basecase created by iPICmini on "+machine_name)
                        data_uuids.append(data_uuid)

                except DataManagerException as err:
                    print("Error registering spaceweahter base result data with data manager, aborting "+err.message)


            workflow.Persist.Put(IncidentID, {'type': 'postprocessed'})
            logs = workflow.Persist.Get(IncidentID)
            print(logs)
    
            completed = 0
            for log in logs:
                if 'type' in log or log['type'] == 'postprocessed':
                    completed = completed + 1

            if completed >= 3:
                print('All simulation completed')
                workflow.send(queue='spaceweather_shutdown', message=msg)
    else:
        print("Ignore originator with "+originator)
        return

#@workflow.handler
#def spaceweather_postprocess(msg):
#    IncidentID = msg["IncidentID"]
#    originator = msg["originator"]
#
#    if originator == 'Simulation Compmleted':
#        workflow.Persist.Put(IncidentID, {'type': 'postprocessed'})
#        logs = workflow.Persist.Get(IncidentID)
#        print(logs)
#
#        completed = 0
#        if len(logs) >= 3:
#            for log in logs:
#                if 'type' in log or log['type'] == 'postprocessed':
#                    completed = completed + 1
#
#        if completed >= 3:
#            print('All simulation completed')
#            workflow.send(queue='spaceweather_shutdown', message=msg)
#    else:
#        workflow.Persist.Put(IncidentID, { 'orginator': originator })

####
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
