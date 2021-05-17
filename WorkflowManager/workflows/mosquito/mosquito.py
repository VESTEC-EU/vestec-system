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
def _launch_simulation(msg, callback='mosquito_postprocess'):
    print("\nMosquito simulation submit handler")
    IncidentID      = msg["IncidentID"]
    CaseName        = msg['SimulationCase']
    Species         = msg['species']
    Disease         = msg['disease']
    SimulationCount = msg['SimulationCount']
    rt              = msg['rt']

    print(msg)
    if CaseName is None:
        print('Case name is none!')
        return

    try:
        callbacks = { 'COMPLETED': callback }
        # ./R0 -a trento -s albopictus -d deng -ns 200 -rt n
        sim_id = createSimulation(IncidentID,
                                  1,
                                  '00:15:00',
                                  CaseName,
                                  'run.sh %s %s %s %d %c' % (CaseName, Species, Disease, SimulationCount, rt),
                                  callbacks,
                                  template_dir='template_mosquito')
        submitSimulation(sim_id)
    except SimulationManagerException as err:
        print("Error creating or submitting simulation "+err.message)
        return

@workflow.handler
def trento(msg):
    print("\nTrento simulation")
    IncidentId = msg["IncidentID"]
    try:
        _launch_simulation(msg)
        workflow.send(queue="mosquito_postprocess", message=msg) # dummy connection
    except e:
        print('Error launching case '+e.message)

@workflow.handler
def rome(msg):
    print("\nRome simulation")
    IncidentId = msg["IncidentID"]
    try:
        _launch_simulation(msg)
        workflow.send(queue="mosquito_postprocess", message=msg) # dummy connection
    except e:
        print('Error launching case '+e.message)
 
# mosquito weather init
@workflow.handler
def mosquito_init(msg):
    print("\nMosquito simulation init handler")
    IncidentID = msg["IncidentID"]

    #workflow.setIncidentActive(IncidentID)

    msg['SimulationCase']  = 'trento'
    msg['species']         = 'albopictus'
    msg['disease']         = 'deng'
    msg['SimulationCount'] = 200
    msg['rt'] = 'n'
    workflow.send(queue="trento", message=msg)

    msg['SimulationCase']  = 'rome'
    msg['species']         = 'aegypti'
    msg['disease']         = 'zika'
    msg['SimulationCount'] = 200
    msg['rt'] = 'y'
    workflow.send(queue="rome", message=msg)

# mosquito weather shutdown
@workflow.handler
def mosquito_postprocess(msg):

    IncidentID = msg["IncidentID"]
    originator = msg['originator']
    logs = workflow.Persist.Get(IncidentID)
    print("\nMosquito simulation postprocess handler", IncidentID)

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
            print(directoryListing)
            for entry in directoryListing:
                tokens=entry.split()
                if len(tokens) == 11 and "exp" in tokens[-1]:
                    result_files[tokens[-1]]=int(tokens[6])

            data_uuids = []
# workflowManager     | R0sim_zika.txt incident-60b96b8096d3/simulation-e1eab7a025f9/exp/aegypti/density_R0_rome 1385541936
# workflowManager     | densitysim.txt incident-60b96b8096d3/simulation-e1eab7a025f9/exp/aegypti/density_R0_rome 2012500373
# workflowManager     | density.txt incident-60b96b8096d3/simulation-e1eab7a025f9/exp/aegypti/density_R0_rome 9434393
# workflowManager     | R0_zika.txt incident-60b96b8096d3/simulation-e1eab7a025f9/exp/aegypti/density_R0_rome 6299184
            for filepath, filesize in result_files.items():
                filename  = os.path.basename(filepath)
                directory = os.path.dirname(filepath)
                print(filename, directory, filesize)

                # register output data with data manager
                try:
                    if ".txt" in filename:
                        description = directory.split('/')
                        data_uuid=registerDataWithDM(filename.replace('(', r'\(').replace(')', r'\)'), machine_name, "mosquito simulation ("+simulation.kind+","+description[-2]+","+description[-1]+")",
                                                     "application/octet-stream", filesize, "txt", path=directory, associate_with_incident=True, incidentId=IncidentID,
                                                     kind=description[-1], comment=description[-2]+" "+description[-1]+" created by R0 on "+machine_name)
                        data_uuids.append(data_uuid)
                    elif '.png' in filename:
                        description = directory.split('/')
                        data_uuid=registerDataWithDM(filename.replace('(', r'\(').replace(')', r'\)'), machine_name, "mosquito simulation ("+simulation.kind+","+description[-2]+","+description[-1]+")",
                                                     "application/octet-stream", filesize, "png", path=directory, associate_with_incident=True, incidentId=IncidentID,
                                                     kind=description[-1], comment=description[-2]+" "+description[-1]+" created by R0 on "+machine_name)
                        data_uuids.append(data_uuid)

                except DataManagerException as err:
                    print("Error registering mosquito result data with data manager, aborting "+err.message)


            workflow.Persist.Put(IncidentID, {'type': 'postprocessed'})
            logs = workflow.Persist.Get(IncidentID)
            print(logs)
    
            completed = 0
            for log in logs:
                if 'type' in log or log['type'] == 'postprocessed':
                    completed = completed + 1

            # only two cases
            if completed >= 2:
                print('All simulation completed')
                workflow.send(queue='mosquito_shutdown', message=msg)
    else:
        print("Ignore originator with "+originator)
        return

#@workflow.handler
#def mosquito_postprocess(msg):
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
#            workflow.send(queue='mosquito_shutdown', message=msg)
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
    #        if log["originator"] == "mosquito_base_simulation"      : _2Dxy=True
    #        if log["originator"] == "mosquito_GuideCase1_simulation": _2DxyGuideCase1=True
    #        if log["originator"] == "mosquito_GuideCase2_simulation": _2DxyGuideCase2=True

    #if _2Dxy is True and _2DxyGuideCase1 is True and _2DxyGuideCase2 is True:
    #    print('Complete incident', IncidentID)
    #    workflow.send(queue="mosquito_shutdown", message=msg)

@workflow.handler
def mosquito_shutdown(msg):
    print("\nMosquito simulation shutdown handler")
    IncidentID = msg["IncidentID"]
    workflow.Complete(IncidentID)

# we have to register them with the workflow system
def RegisterHandles():
    workflow.RegisterHandler(handler=trento,               queue="trento")
    workflow.RegisterHandler(handler=rome,                 queue="rome")
    workflow.RegisterHandler(handler=mosquito_init,        queue="mosquito_init")
    workflow.RegisterHandler(handler=mosquito_postprocess, queue="mosquito_postprocess")
    workflow.RegisterHandler(handler=mosquito_shutdown,    queue="mosquito_shutdown")
