import os
import requests

def createSimulation(incident_id, num_nodes, requested_walltime, kind, executable, queuestate_callbacks={}, directory=None, template_dir=None):

    arguments = {   'incident_id': incident_id, 
                    'num_nodes':num_nodes,
                    'requested_walltime' : requested_walltime, 
                    'kind':kind, 
                    'executable':executable, 
                    'queuestate_calls':queuestate_callbacks }
    
    if directory is not None:
        arguments["directory"]=directory
    if template_dir is not None:
        arguments["template_dir"]=template_dir

    createResponse = requests.post(_get_SM_URL()+'/create', json=arguments)
    return createResponse.json()["simulation_id"]

def submitSimulation(sim_id):
    submitobj = {'simulation_uuid' : sim_id}
    response = requests.post(_get_SM_URL()+'/submit', json=submitobj)

def refreshSimilation(sim_id):
    requests.post(_get_SM_URL()+'/refresh/'+sim_id)

def cancelSimulation(sim_id):
    requests.delete(_get_SM_URL()+'/simulation/'+sim_id)

def getHealth():
    try:
        health_status = requests.get(_get_SM_URL() + '/health')        
        return health_status.status_code == 200            
    except:
        return False

def _get_SM_URL():
    if "VESTEC_SM_URI" in os.environ:
        return os.environ["VESTEC_SM_URI"]
    else:
        return 'http://localhost:5505/SM'