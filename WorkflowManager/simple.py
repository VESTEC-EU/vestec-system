import workflow
import pony.orm as pny
import datetime
import time
import requests

if "VESTEC_EDI_URI" in os.environ:    
    EDI_URL= os.environ["VESTEC_EDI_URI"]
else:    
    EDI_URL= 'http://localhost:5501/EDImanager'

# we now want to define some handlers
@workflow.handler
def external_data_arrival_handler(message):
    print("Got some external data from "+message["data"]["source"])
    workflow.Complete(message["IncidentID"])

@workflow.handler
def initialise_simple(message):
    print("Initialise simple workflow for "+message["IncidentID"])
    myobj = {'queuename': 'external_data_arrival', 'incidentid':message["IncidentID"], 'endpoint':'editest'}
    x = requests.post(EDI_url+"/register", json = myobj)
    print("EDI response" + x.text)
    workflow.setIncidentActive(message["IncidentID"])

# we have to register them with the workflow system
def RegisterHandlers():
    workflow.RegisterHandler(external_data_arrival_handler, "external_data_arrival")
    workflow.RegisterHandler(initialise_simple, "initialise_simple")
