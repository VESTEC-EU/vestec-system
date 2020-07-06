import os
import requests

def getAllEDIEndpoints():
    edi_info = requests.get(_get_EDI_URL() + '/list')    
    return edi_info.json()

def getEndpointInformation(endpoint):
    edi_info = requests.get(_get_EDI_URL() + '/list/'+endpoint)    
    return edi_info.json()

def removeEndpoint(incidentid, endpoint, queuename, pollperiod=None):
    arguments = {   'queuename': queuename, 
                    'incidentid':incidentid,
                    'endpoint' : endpoint }
    if pollperiod is not None:
        arguments["pollperiod"]=pollperiod

    requests.post(_get_EDI_URL()+'/remove', data=arguments)

def registerEndpoint(incidentid, queuename, endpoint, pollperiod=None)
    arguments = {   'queuename': queuename, 
                    'incidentid':incidentid,
                    'endpoint' : endpoint }
    if pollperiod is not None:
        arguments["pollperiod"]=pollperiod

    requests.post(_get_EDI_URL()+'/register', data=arguments)

def getHealth():
    try:
        health_status = requests.get(_get_EDI_URL() + '/health')        
        return health_status.status_code == 200            
    except:
        return False

def _get_EDI_URL():
    if "VESTEC_EDI_URI" in os.environ:
        return os.environ["VESTEC_EDI_URI"]
    else:
        return 'http://localhost:5501/EDImanager'