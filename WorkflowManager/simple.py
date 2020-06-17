import sys
sys.path.append("../")
import workflow
import os
import pony.orm as pny
import datetime
import time
import requests
import json
from base64 import b64decode
from Database import LocalDataStorage
from Database.workflow import Incident, StoredDataset

if "VESTEC_EDI_URI" in os.environ:    
    EDI_URL= os.environ["VESTEC_EDI_URI"]
    SM_URL= os.environ["VESTEC_SM_URI"]
    DATA_MANAGER_URI = os.environ["VESTEC_DM_URI"]
else:    
    EDI_URL= 'http://localhost:5501/EDImanager'
    DATA_MANAGER_URI = 'http://localhost:5000/DM'
    SM_URL = 'http://localhost:5505/SM'

# we now want to define some handlers
@workflow.handler
def external_data_arrival_handler(message):
    print("Got some external data from "+message["data"]["source"])
    workflow.Complete(message["IncidentID"])

@workflow.handler
@pny.db_session
def manually_add_data(message):
    file_contents_to_add = json.loads(message["data"]["payload"])
    header, encoded = file_contents_to_add["payload"].split(",", 1)
    filetype=header.split(":", 1)[1].split(";", 1)[0]
    data = b64decode(encoded)

    new_file = LocalDataStorage(contents=data, filename=file_contents_to_add["filename"], filetype=filetype)
    pny.commit()    

    myobj = {'filename': str(new_file.uuid), 'path':'vestecDB', 'machine':'VESTECSERVER', 'description':'manually uploaded', 'size':str(len(data)), 'originator':'manually added','group' : 'none'}
    x = requests.put(DATA_MANAGER_URI+'/register', data=myobj)    
    incidentId=message["IncidentID"]
    incident=Incident[incidentId]
    incident.associated_datasets.create(
        uuid=x.text, name=file_contents_to_add["filename"], 
        type=file_contents_to_add["filetype"], 
        comment=file_contents_to_add["filecomment"],         
        date_created=datetime.datetime.now())    
    pny.commit()

@workflow.handler
def test_workflow(message):
    print("Test called!")
    callbacks = {'COMPLETED': 'simple_workflow_execution_completed'}
    myobj = {'incident_id': message["IncidentID"], 'num_nodes': 100, 'requested_walltime': 120, 'kind': 'test run', 'executable': 'subtest.pbs', 'directory': 'vestec_test', 'queuestate_calls':callbacks}
    x = requests.post(SM_URL+'/create', json=myobj)
    print(x.json())

@workflow.handler
def simple_workflow_execution_completed(message):
    print("Stage completed with simulation ID "+message["simulationId"])

@workflow.handler
def initialise_simple(message):
    print("Initialise simple workflow for "+message["IncidentID"])
    myobj = {'queuename': 'external_data_arrival', 'incidentid':message["IncidentID"], 'endpoint':'editest'}
    x = requests.post(EDI_URL+"/register", json = myobj)
    print("EDI response for external data arrival" + x.text)

    myobj = {'queuename': 'add_data_simple', 'incidentid':message["IncidentID"], 'endpoint':'add_data_simple'+message["IncidentID"]}
    x = requests.post(EDI_URL+"/register", json = myobj)
    print("EDI response for manually add data" + x.text)

    myobj = {'queuename': 'test_workflow_simple', 'incidentid':message["IncidentID"], 'endpoint':'test_stage_'+message["IncidentID"]}
    x = requests.post(EDI_URL+"/register", json = myobj)     

    workflow.setIncidentActive(message["IncidentID"])

# we have to register them with the workflow system
def RegisterHandlers():
    workflow.RegisterHandler(external_data_arrival_handler, "external_data_arrival")
    workflow.RegisterHandler(manually_add_data, "add_data_simple")
    workflow.RegisterHandler(test_workflow, "test_workflow_simple")
    workflow.RegisterHandler(initialise_simple, "initialise_simple")
    workflow.RegisterHandler(simple_workflow_execution_completed, "simple_workflow_execution_completed")
