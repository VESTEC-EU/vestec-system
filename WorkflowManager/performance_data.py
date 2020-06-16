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
    DATA_MANAGER_URI = os.environ["VESTEC_DM_URI"]
else:
    EDI_URL= 'http://localhost:5501/EDImanager'
    DATA_MANAGER_URI = 'http://localhost:5000/DM'

# we now want to define some handlers
@workflow.handler
@pny.db_session
def add_performance_data(message):
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
def initialise_performance_data(message):
    print("Initialise simple workflow for "+message["IncidentID"])
    myobj = {'queuename': 'add_performance_data', 'incidentid':message["IncidentID"], 'endpoint':'add_performance_data'+message["IncidentID"]}
    x = requests.post(EDI_URL+"/register", json = myobj)
    print("EDI response for manually add data" + x.text)
    workflow.setIncidentActive(message["IncidentID"])

# we have to register them with the workflow system
def RegisterHandlers():
    workflow.RegisterHandler(add_performance_data, "add_data_simple")
    workflow.RegisterHandler(initialise_performance_data, "initialise_simple")
