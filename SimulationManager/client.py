import os
import requests
import json

class SimulationManagerException(Exception):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message

def createSimulation(incident_id, num_nodes, requested_walltime, kind, executable, queuestate_callbacks={}, directory=None, template_dir=None, comment=None, number_instances=1):

    arguments = {   'incident_id': incident_id, 
                    'num_nodes':num_nodes,
                    'requested_walltime' : requested_walltime, 
                    'kind':kind, 
                    'executable':executable, 
                    'number_instances':number_instances,
                    'queuestate_calls':queuestate_callbacks }
    
    if directory is not None:
        arguments["directory"]=directory
    if comment is not None:
        arguments["comment"]=comment
    if template_dir is not None:
        arguments["template_dir"]=template_dir

    createResponse = requests.post(_get_SM_URL()+'/create', json=arguments)
    if createResponse.status_code == 201:
        return createResponse.json()["simulation_id"]
    else:
        raise SimulationManagerException(createResponse.status_code, createResponse.text)

def submitSimulation(sim_id):
    submitobj = {'simulation_uuid' : sim_id}
    response = requests.post(_get_SM_URL()+'/submit', json=submitobj)
    if response.status_code != 200:
        raise SimulationManagerException(response.status_code, response.text)

def groupSimulations(sim_ids):
    submitobj = {'simulation_uuids' : sim_ids}
    response = requests.post(_get_SM_URL()+'/group', json=submitobj)
    if response.status_code != 200:
        raise SimulationManagerException(response.status_code, response.text)

def refreshSimilation(sim_id):
    response = requests.post(_get_SM_URL()+'/refresh/'+sim_id)
    if response.status_code != 200:
        raise SimulationManagerException(response.status_code, response.text)

def cancelSimulation(sim_id):
    response = requests.delete(_get_SM_URL()+'/simulation/'+sim_id)
    if response.status_code != 200:
        raise SimulationManagerException(response.status_code, response.text)

#returns information about the simulation with sim_id as a dictionary
def getSimulationInfo(sim_id):
    response = requests.get(_get_SM_URL()+'/info/'+sim_id)
    if response.status_code != 200:
        raise SimulationManagerException(response.status_code, response.text)
    return json.loads(response.text)

def getSMHealth():
    try:
        health_status = requests.get(_get_SM_URL() + '/health')        
        return health_status.status_code == 200            
    except:
        return False

def _get_SM_URL():
    if "VESTEC_SM_URI" in os.environ:
        return os.environ["VESTEC_SM_URI"]
    else:
        return 'http://localhost:5500/SM'