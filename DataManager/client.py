import os
import requests
import pony.orm as pny
from Database import Incident, StoredDataset
import Utils.log as log
import datetime

logger = log.VestecLogger("Data Manager")

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
        if incidentId is not None: logger.Log("Registered file '"+filename+"' on machine '"+machine+"'", "system", incidentId)
        return returnUUID.text
    else:
        if incidentId is not None: logger.Log("Error registering file '"+filename+"' on machine '"+machine+"' message '"+returnUUID.text+";", "system", incidentId, type=log.LogType.Error)
        raise DataManagerException(returnUUID.status_code, returnUUID.text)

def searchForDataInDM(filename, machine, path=None):
    appendStr="filename="+filename+"&machine="+machine
    if path is not None:
        appendStr+="&path="+path

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

def getByteDataViaDM(data_uuid, gather_metrics=False):
    arguments = { 'gather_metrics':gather_metrics }

    retrieved_data=requests.get(_get_DM_URL()+'/get/'+data_uuid, data=arguments)    
    if retrieved_data.status_code == 200:        
        return retrieved_data.content
    else:
        raise DataManagerException(retrieved_data.status_code, retrieved_data.text)

def putByteDataViaDM(filename, machine, description, type, originator, payload, group = "none", storage_technology=None, path=None, 
        associate_with_incident=False, incidentId=None, kind="", comment=None, gather_metrics=False):
    if associate_with_incident and incidentId is None:
        raise DataManagerException(400, "Must supply an incident ID when associating dataset with an incident")

    arguments = {   'filename': filename, 
                    'machine':machine,
                    'storage_technology' : storage_technology, 
                    'description':description, 
                    'type':type,
                    'payload':payload, 
                    'originator':originator,
                    'group' : group,
                    'gather_metrics':gather_metrics }
    if storage_technology is not None:
        arguments["storage_technology"]=storage_technology
    if path is not None:
        arguments["path"]=path

    response=requests.put(_get_DM_URL()+'/put', data=arguments)
    if response.status_code == 201:
        if associate_with_incident:
            if comment is None: comment=description
            _associateDataWithIncident(incidentId, response.text, filename, kind, comment)
        if incidentId is not None: logger.Log("Put data with name '"+filename+"' onto machine '"+machine+"'", "system", incidentId)
        return response.text
    else:
        if incidentId is not None: logger.Log("Error putting data with name '"+filename+"' on machine '"+machine+"' message '"+response.text+"'", "system", incidentId, type=log.LogType.Error)
        raise DataManagerException(response.status_code, response.text)

def _issueDataDownloadToDM(filename, machine, description, type, originator, url, protocol, group = "none", storage_technology=None, path=None, options=None,
        associate_with_incident=False, incidentId=None, kind="", comment=None, callback=None):
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
    if callback is not None and incidentId is not None:
        arguments["callback"]=callback
        arguments["incidentId"]=incidentId

    returnUUID = requests.put(_get_DM_URL()+'/getexternal', data=arguments)
    if returnUUID.status_code == 201:
        if associate_with_incident:
            if comment is None: comment=description
            _associateDataWithIncident(incidentId, returnUUID.text, filename, kind, comment)
        if incidentId is not None: logger.Log("Downloaded data from '"+url+"' data with name '"+filename+"' onto machine '"+machine+"'", "system", incidentId)
        return returnUUID.text
    else:
        if incidentId is not None: logger.Log("Error downloading data from '"+url+"' data message '"+returnUUID.text+"'", "system", incidentId, type=log.LogType.Error)
        raise DataManagerException(returnUUID.status_code, returnUUID.text)

def downloadDataToTargetViaDM(filename, machine, description, type, originator, url, protocol, group = "none", storage_technology=None, path=None, options=None,
        associate_with_incident=False, incidentId=None, kind="", comment=None, callback=None):
    if associate_with_incident and incidentId is None:
        raise DataManagerException(400, "Must supply an incident ID when associating dataset with an incident")
    if callback and incidentId is None:
        raise DataManagerException(400, "Must supply an incident ID when providing a callback for nonblocking download")

    if isinstance(filename, list) and isinstance(url, list) and isinstance(path, list):
        dataUUIDs=[]
        for (a, b, c) in zip(filename, url, path):
            dataUUIDs.append(_issueDataDownloadToDM(a, machine, description, type, b, url, protocol, group, storage_technology, c, options,
                associate_with_incident, incidentId, kind, comment, callback))
    elif not isinstance(filename, list) and not isinstance(url, list) and not isinstance(path, list):
        return _issueDataDownloadToDM(filename, machine, description, type, originator, url, protocol, group, storage_technology, path, options,
            associate_with_incident, incidentId, kind, comment, callback)
    else:
        raise DataManagerException(400, "Passing a mix of lists and single values for multiple download, filename, url and path must be a list for multiple downloads")
    

def moveDataViaDM(data_uuid, dest_name, dest_machine, dest_storage_technology=None, gather_metrics=True):
    arguments = {   'dest': dest_name, 
                    'machine':dest_machine,
                    'gather_metrics':gather_metrics }
    if dest_storage_technology is not None:
        arguments["storage_technology"]=dest_storage_technology

    response=requests.post(_get_DM_URL()+'/move/'+data_uuid, data=arguments)
    if response.status_code == 201:
        id = response.text
        #if this file is associated with an incident make sure its filename is updated in the database 
        _renameAssociatedData(id, os.path.split(dest_name)[1])
        return response.text
    else:
        raise DataManagerException(response.status_code, response.text)

def copyDataViaDM(data_uuid, dest_name, dest_machine, dest_storage_technology=None, gather_metrics=True,associate_with_incident=False, incident=None, kind=""):
    arguments = {   'dest': dest_name, 
                    'machine':dest_machine,
                    'gather_metrics':gather_metrics }
    if dest_storage_technology is not None:
        arguments["storage_technology"]=dest_storage_technology

    if associate_with_incident and incident is None:
        raise DataManagerException(400, "Must supply an incident ID when associating dataset with an incident")

    response=requests.post(_get_DM_URL()+'/copy/'+data_uuid, data=arguments)
    if response.status_code == 201:
        id = response.text
        #if requested, make sure this copy is associated with the requested incident
        if associate_with_incident: 
            data = getInfoForDataInDM(id)
            name = data["filename"]
            comment = "Copy of %s"%(data_uuid)
            _associateDataWithIncident(incident, id, name, kind, comment)        
        return id
    else:
        raise DataManagerException(response.status_code, response.text)

def deleteDataViaDM(data_uuid):
    response=requests.delete(_get_DM_URL()+'/remove/'+data_uuid)
    if response.status_code != 200:
        raise DataManagerException(response.status_code, response.text)

def predictDatasetTransferPerformance(data_uuid, dest_machine):
    arguments={ 'uuid' : data_uuid, 'dest_machine' : dest_machine }
    response=requests.post(_get_DM_URL()+'/predict', data=arguments)
    if response.status_code == 201:        
        return response.json()["prediction_time"]
    else:
        raise DataManagerException(response.status_code, response.text)

def predictDataTransferPerformance(src_machine, dest_machine, data_size):
    arguments={ 'src_machine' : src_machine, 'dest_machine' : dest_machine, 'data_size' : data_size }
    response=requests.post(_get_DM_URL()+'/predict', data=arguments)
    if response.status_code == 201:        
        return response.json()["prediction_time"]
    else:
        raise DataManagerException(response.status_code, response.text)

def getDMHealth():
    try:
        health_status = requests.get(_get_DM_URL() + '/health')        
        return health_status.status_code == 200            
    except:
        return False

def getLocalFilePathPrepend():
    if "VESTEC_SHARED_FILE_LOCATION" in os.environ:
        shared_location= os.environ["VESTEC_SHARED_FILE_LOCATION"]
        if shared_location[-1] != "/": shared_location+="/"
        return shared_location
    else:
        return ""

def _get_DM_URL():
    if "VESTEC_DM_URI" in os.environ:
        return os.environ["VESTEC_DM_URI"]
    else:
        return 'http://localhost:5503/DM'

@pny.db_session
def _associateDataWithIncident(IncidentID, data_uuid, name, type, comment):
    incident=Incident[IncidentID]
    incident.associated_datasets.create(uuid=data_uuid, name=name, type=type, comment=comment, date_created=datetime.datetime.now())

#If a file is moved, make sure that it's filaname in the StoredDataset table is correct 
@pny.db_session
def _renameAssociatedData(data_uuid, newname):
    try:
        dataset = StoredDataset.get(uuid=data_uuid)
        dataset.name = newname
    except pny.core.ObjectNotFound:
        pass
    
    