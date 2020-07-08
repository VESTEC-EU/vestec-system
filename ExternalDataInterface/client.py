import os
import requests

class ExternalDataInterfaceException(Exception):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message

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

    status=requests.post(_get_EDI_URL()+'/remove', json=arguments)
    if status.status_code != 200:
        raise ExternalDataInterfaceException(status.status_code, status.json()["msg"])

def registerEndpoint(incidentid, endpoint, queuename, pollperiod=None):
    arguments = {   'queuename': queuename, 
                    'incidentid':incidentid,
                    'endpoint' : endpoint }
    if pollperiod is not None:
        arguments["pollperiod"]=pollperiod

    status=requests.post(_get_EDI_URL()+'/register', json=arguments)
    if status.status_code != 201:
        raise ExternalDataInterfaceException(status.status_code, status.json()["msg"])

def getEDIHealth():
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