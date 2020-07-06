import os
import requests

def registerDataWithDM(filename, machine, description, size, originator, group = "none", storage_technology=None, path=None):
    arguments = {   'filename': filename, 
                    'machine':machine,
                    'storage_technology' : storage_technology, 
                    'description':description, 
                    'size':size, 
                    'originator':originator,
                    'group' : group }
    if storage_technology is not None:
        arguments["storage_technology"]=storage_technology
    if path is not None:
        arguments["path"]=path

    returnUUID = requests.put(_get_DM_URL()+'/register', data=arguments)
    return returnUUID.text

def searchForDataInDM(filename, machine, path=None):
    appendStr="filename="+machine+"&machine="+machine
    if path is not None:
        appendStr+="path="+path
    foundDataResponse = requests.get(_get_DM_URL()+'/search?'+appendStr)
    return foundDataResponse.json()

def getInfoForDataInDM(data_uuid=None):
    if data_uuid is not None:
        response=requests.get(_get_DM_URL()+'/info/'+data_uuid)
    else:
        response=requests.get(_get_DM_URL()+'/info')
    return response.json()

def getByteDataViaDM(data_uuid):
    retrieved_data=requests.get(_get_DM_URL()+'/get/'+data_uuid)
    return retrieved_data.text

def putByteDataViaDM(filename, machine, description, originator, payload, group = "none", storage_technology=None, path=None):
    arguments = {   'filename': filename, 
                    'machine':machine,
                    'storage_technology' : storage_technology, 
                    'description':description, 
                    'payload':payload, 
                    'originator':originator,
                    'group' : group }
    if storage_technology is not None:
        arguments["storage_technology"]=storage_technology
    if path is not None:
        arguments["path"]=path

    response=requests.put(_get_DM_URL()+'/put', data=arguments)
    return response.text

def downloadDataToTargetViaDM(filename, machine, description, originator, url, protocol, group = "none", storage_technology=None, path=None, options=None ):
    arguments = {   'filename': filename, 
                    'machine':machine,
                    'storage_technology' : storage_technology, 
                    'description':description, 
                    'url':url, 
                    'protcol':protcol, 
                    'originator':originator,
                    'group' : group }
    if storage_technology is not None:
        arguments["storage_technology"]=storage_technology
    if path is not None:
        arguments["path"]=path
    if options is not None:
        arguments["options"]=options

    returnUUID = requests.put(_get_DM_URL()+'/getexternal', data=arguments)
    return returnUUID.text

def moveDataViaDM(data_uuid):
    response=requests.post(_get_DM_URL()+'/move/'+data_uuid)
    return response.text

def copyDataViaDM(data_uuid):
    response=requests.post(_get_DM_URL()+'/copy/'+data_uuid)
    return response.text

def deleteDataViaDM(data_uuid):
    requests.delete(_get_DM_URL()+'/remove/'+data_uuid)

def getHealth():
    try:
        health_status = requests.get(_get_DM_URL() + '/health')        
        return health_status.status_code == 200            
    except:
        return False

def _get_DM_URL():
    if "VESTEC_DM_URI" in os.environ:
        return os.environ["VESTEC_DM_URI"]
    else:
        return 'http://localhost:5000/DM'