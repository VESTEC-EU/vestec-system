import os
import requests
import pony.orm as pny
from Database import Incident
import datetime

class DataManagerException(Exception):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message

def registerDataWithDM(filename, machine, description, type, size, originator, group = "none", storage_technology=None, path=None, 
        associate_with_incident=False, incidentId=None, kind="", comment=None):
    if associate_with_incident and incidentId is None:
        raise DataManagerException(400, "Must supply an incident ID when associating dataset with an incident")

    arguments = {   'filename': filename, 
                    'machine':machine,
                    'storage_technology' : storage_technology, 
                    'description':description, 
                    'type':type,
                    'size':size, 
                    'originator':originator,
                    'group' : group }
    if storage_technology is not None:
        arguments["storage_technology"]=storage_technology
    if path is not None:
        arguments["path"]=path        

    returnUUID = requests.put(_get_DM_URL()+'/register', data=arguments)
    if returnUUID.status_code == 201:
        if associate_with_incident:
            if comment is None: comment=description
            _associateDataWithIncident(incidentId, returnUUID.text, filename, kind, comment)
        return returnUUID.text
    else:
        raise DataManagerException(returnUUID.status_code, returnUUID.text)

def searchForDataInDM(filename, machine, path=None):
    appendStr="filename="+machine+"&machine="+machine
    if path is not None:
        appendStr+="path="+path
    foundDataResponse = requests.get(_get_DM_URL()+'/search?'+appendStr)
    if foundDataResponse.status_code == 200:
        return foundDataResponse.json()
    else:
        raise DataManagerException(foundDataResponse.status_code, foundDataResponse.text)

def getInfoForDataInDM(data_uuid=None):
    if data_uuid is not None:
        response=requests.get(_get_DM_URL()+'/info/'+data_uuid)
    else:
        response=requests.get(_get_DM_URL()+'/info')
    if response.status_code == 200:
        return response.json()
    else:
        raise DataManagerException(response.status_code, response.text)

def getByteDataViaDM(data_uuid):
    retrieved_data=requests.get(_get_DM_URL()+'/get/'+data_uuid)
    if retrieved_data.status_code == 200:
        return retrieved_data.text
    else:
        raise DataManagerException(retrieved_data.status_code, retrieved_data.text)

def putByteDataViaDM(filename, machine, description, type, originator, payload, group = "none", storage_technology=None, path=None, 
        associate_with_incident=False, incidentId=None, kind="", comment=None):
    if associate_with_incident and incidentId is None:
        raise DataManagerException(400, "Must supply an incident ID when associating dataset with an incident")

    arguments = {   'filename': filename, 
                    'machine':machine,
                    'storage_technology' : storage_technology, 
                    'description':description, 
                    'type':type,
                    'payload':payload, 
                    'originator':originator,
                    'group' : group }
    if storage_technology is not None:
        arguments["storage_technology"]=storage_technology
    if path is not None:
        arguments["path"]=path

    response=requests.put(_get_DM_URL()+'/put', data=arguments)
    if response.status_code == 201:
        if associate_with_incident:
            if comment is None: comment=description
            _associateDataWithIncident(incidentId, returnUUID.text, filename, kind, comment)
        return response.text
    else:
        raise DataManagerException(response.status_code, response.text)

def downloadDataToTargetViaDM(filename, machine, description, type, originator, url, protocol, group = "none", storage_technology=None, path=None, options=None,
        associate_with_incident=False, incidentId=None, kind="", comment=None):
    if associate_with_incident and incidentId is None:
        raise DataManagerException(400, "Must supply an incident ID when associating dataset with an incident")

    arguments = {   'filename': filename, 
                    'machine':machine,
                    'storage_technology' : storage_technology, 
                    'description':description, 
                    'type':type,
                    'url':url, 
                    'protocol':protocol, 
                    'originator':originator,
                    'group' : group }
    if storage_technology is not None:
        arguments["storage_technology"]=storage_technology
    if path is not None:
        arguments["path"]=path
    if options is not None:
        arguments["options"]=options

    returnUUID = requests.put(_get_DM_URL()+'/getexternal', data=arguments)
    if returnUUID.status_code == 201:
        if associate_with_incident:
            if comment is None: comment=description
            _associateDataWithIncident(incidentId, returnUUID.text, filename, kind, comment)
        return returnUUID.text
    else:
        raise DataManagerException(returnUUID.status_code, returnUUID.text)

def moveDataViaDM(data_uuid, dest_name, dest_machine, dest_storage_technology=None):
    arguments = {   'dest': dest_name, 
                    'machine':dest_machine }
    if dest_storage_technology is not None:
        arguments["storage_technology"]=dest_storage_technology

    response=requests.post(_get_DM_URL()+'/move/'+data_uuid, data=arguments)
    if response.status_code == 201:
        return response.text
    else:
        raise DataManagerException(response.status_code, response.text)

def copyDataViaDM(data_uuid, dest_name, dest_machine, dest_storage_technology=None):
    arguments = {   'dest': dest_name, 
                    'machine':dest_machine }
    if dest_storage_technology is not None:
        arguments["storage_technology"]=dest_storage_technology

    response=requests.post(_get_DM_URL()+'/copy/'+data_uuid, data=arguments)
    if response.status_code == 201:
        return response.text
    else:
        raise DataManagerException(response.status_code, response.text)

def deleteDataViaDM(data_uuid):
    response=requests.delete(_get_DM_URL()+'/remove/'+data_uuid)
    if response.status_code != 200:
        raise DataManagerException(response.status_code, response.text)

def getDMHealth():
    try:
        health_status = requests.get(_get_DM_URL() + '/health')        
        return health_status.status_code == 200            
    except:
        return False

def _get_DM_URL():
    if "VESTEC_DM_URI" in os.environ:
        return os.environ["VESTEC_DM_URI"]
    else:
        return 'http://localhost:5503/DM'

@pny.db_session
def _associateDataWithIncident(IncidentID, data_uuid, name, type, comment):
    incident=Incident[IncidentID]
    incident.associated_datasets.create(uuid=data_uuid, name=name, type=type, comment=comment, date_created=datetime.datetime.now())