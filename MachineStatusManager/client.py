import os
import requests

class MachineStatusManagerException(Exception):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message

def retrieveMachineStatuses():
    machine_statuses=requests.get(_get_MSM_URL() + '/machinestatuses')
    return machine_statuses.json()

def addNewMachine(machine_name, host_name, scheduler, connection_type, num_nodes, cores_per_node, base_work_dir):
    arguments = {   'machine_name': machine_name, 
                    'host_name':host_name,
                    'scheduler' : scheduler, 
                    'connection_type':connection_type, 
                    'num_nodes':num_nodes,
                    'cores_per_node':cores_per_node,
                    'base_work_dir':base_work_dir  }

    created_info = requests.post(_get_MSM_URL() + '/add', json=arguments)

def matchBestMachine(walltime, num_nodes):
    matched_machine=requests.get(_get_MSM_URL() + '/matchmachine?walltime='+str(walltime)+'&num_nodes='+str(num_nodes))
    if matched_machine.status_code == 200:
        return matched_machine.json()["machine_id"]             
    else:    
        raise MachineStatusManagerException(matched_machine.status_code, matched_machine.json()["msg"])            

def enableTestModeOnMachine(machine_id):
    requests.post(_get_MSM_URL() + '/enable_testmode/'+machine_id)

def disableTestModeOnMachine(machine_id):
    requests.post(_get_MSM_URL() + '/disable_testmode/'+machine_id)

def enableMachine(machine_id):
    requests.post(_get_MSM_URL() + '/enable/'+machine_id)

def disableMachine(machine_id):
    requests.post(_get_MSM_URL() + '/disable/'+machine_id)

def deleteMachine(machine_id):
    requests.delete(_get_MSM_URL() + '/machine/'+machine_id)

def getHealth():
    try:
        health_status = requests.get(_get_MSM_URL() + '/health')        
        return health_status.status_code == 200            
    except:
        return False

def _get_MSM_URL():
    if "VESTEC_MSM_URI" in os.environ:
        return os.environ["VESTEC_MSM_URI"]
    else:
        return 'http://localhost:5502/MSM'