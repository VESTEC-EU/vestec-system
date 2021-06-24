import sys
#sys.path.append("../")
from manager import workflow
import os
import pony.orm as pny
import datetime
import time
import yaml
import json
from base64 import b64decode
from Database import LocalDataStorage
from Database.workflow import Simulation, Incident
#from DataManager.client import registerDataWithDM, putByteDataViaDM, DataManagerException
from DataManager.client import moveDataViaDM, DataManagerException, getInfoForDataInDM, putByteDataViaDM, registerDataWithDM, copyDataViaDM, getLocalFilePathPrepend
from SimulationManager.client import createSimulation, submitSimulation, SimulationManagerException
from ExternalDataInterface.client import registerEndpoint, ExternalDataInterfaceException, removeEndpoint

# create and submit jobs
def _launch_simulation(IncidentID, species, disease, region, count, callback='mosquito_postprocess'):
    try:
        callbacks = { 'COMPLETED': callback }
        # ./R0 -a trento -s albopictus -d deng -ns 200 -rt n
        sim_id = createSimulation(IncidentID, 1, "00:15:00", "Mosquito simulation", "submit.sh", callbacks, template_dir="templates/mosquito_template")
        with pny.db_session:
            simulation=Simulation[sim_id]    
            machine_name=simulation.machine.machine_name            

        try:                
            putByteDataViaDM("mosquito.yml", machine_name, "Mosquito simulation configuration", "text/plain", "Mosquito workflow", _buildMosquitoYaml(species, disease, region, count), path=simulation.directory)                 
        except DataManagerException as err:
            print("Can not write mosquito configuration to simulation location"+err.message)        

        submitSimulation(sim_id)
    except SimulationManagerException as err:
        print("Error creating or submitting simulation "+err.message)
        return

@pny.db_session
def _buildMosquitoYaml(species, disease, region, count):
    sample_configuration_file = open("workflows/mosquito/templates/mosquito.yml")
    yaml_template = yaml.load(sample_configuration_file, Loader=yaml.FullLoader)        

    static_directory="/lustre/home/dc118/shared/data/moz"
    
    yaml_template["region"]=region
    yaml_template["species"]=species
    yaml_template["disease"]=disease
    yaml_template["count"]=count
    yaml_template["region_covariates"]["path"]=static_directory+"/"+region+"/lm_covariates_"+region+"_not_filtered.csv"
    yaml_template["temperature_data"]["path"]=static_directory+"/"+region+"/wc_temp_"+region+".csv"
    yaml_template["species_user_parameters"]["path"]="data/"+species+"_parameter.txt"
    yaml_template["species_fixed_parameters"]["path"]="data/"+species+"_parameter_fixed.txt"
    yaml_template["species_alpha_distribution"]["path"]="data/"+species+"_alpha_w_k_m_wc_lm_within_fit_cumulato_best_dic.txt"
    yaml_template["species_covariate_distribution"]["path"]="data/"+species+"_coeff_covariate_wc_lm_within_fit_cumulato_best_dic.txt"
    yaml_template["disease_species_user_parameters"]["path"]="data/"+disease+"_"+species+"_parameter_user.txt"    
        
    return yaml.dump(yaml_template)

def trento(IncidentId):    
    _launch_simulation(IncidentId, 'albopictus', 'deng', 'trento', 200)    

def rome(IncidentId):    
    _launch_simulation(IncidentId, 'aegypti', 'zika', 'rome', 200)

@workflow.handler
def mosquito_test(msg):
    print("\nMosquito test handler called to start rome and trento simulations")
    IncidentID = msg["IncidentID"]
    trento(IncidentID)
    rome(IncidentID)
 
# mosquito weather init
@workflow.handler
def mosquito_init(msg):
    try:
        registerEndpoint(msg["IncidentID"], "test_stage_"+msg["IncidentID"], "mosquito_test")
    except ExternalDataInterfaceException as err:
        print("Error from EDI on registration "+err.message)

    workflow.setIncidentActive(msg["IncidentID"])
    

# mosquito weather shutdown
@workflow.handler
def mosquito_postprocess(msg):

    IncidentID = msg["IncidentID"]
    originator = msg['originator']
    logs = workflow.Persist.Get(IncidentID)
    print("\nMosquito simulation postprocess handler", IncidentID)

    if originator == 'Simulation Completed':
        simulationId = msg["simulationId"]
        simulationIdPostfix=simulationId.split("-")[-1]
        directoryListing=msg["directoryListing"]

        print("\nResults available for mosquito simulation!") 

        with pny.db_session:
            myincident = Incident[IncidentID]
            simulation=Simulation[simulationId]
            machine_name=simulation.machine.machine_name
            machine_basedir=simulation.machine.base_work_dir
            if machine_basedir[-1] != "/": machine_basedir+="/"

        if simulation is not None:
            result_files={}            
            for entry in directoryListing:
                tokens=entry.split()
                if len(tokens) == 9 and ".txt" in tokens[-1]:
                    if tokens[4].isnumeric():
                        file_size=int(tokens[4])
                    else:
                        file_size=0
                    registerDataWithDM(tokens[-1], machine_name, "Mosquito simulation", "text/plain", file_size, "Mosquito output txt", 
                        path=simulation.directory, associate_with_incident=True, incidentId=IncidentID, kind="Mosquito simulation output", 
                        comment="Created by mosquito on "+machine_name+" with simulation ID "+simulationId)
                    print("Register "+tokens[-1])

            data_uuids = []
            for filepath, filesize in result_files.items():
                filename  = os.path.basename(filepath)
                directory = os.path.dirname(filepath)
                print(filename, directory, filesize)

                # register output data with data manager
                try:
                    if ".txt" in filename:
                        description = directory.split('/')
                        data_uuid=registerDataWithDM(filename.replace('(', r'\(').replace(')', r'\)'), machine_name, "mosquito simulation ("+simulation.kind+","+description[-2]+","+description[-1]+")",
                                                     "application/octet-stream", filesize, "txt", path=directory, associate_with_incident=True, incidentId=IncidentID,
                                                     kind=description[-1], comment=description[-2]+" "+description[-1]+" created by R0 on "+machine_name)
                        data_uuids.append(data_uuid)
                    elif '.png' in filename:
                        description = directory.split('/')
                        data_uuid=registerDataWithDM(filename.replace('(', r'\(').replace(')', r'\)'), machine_name, "mosquito simulation ("+simulation.kind+","+description[-2]+","+description[-1]+")",
                                                     "application/octet-stream", filesize, "png", path=directory, associate_with_incident=True, incidentId=IncidentID,
                                                     kind=description[-1], comment=description[-2]+" "+description[-1]+" created by R0 on "+machine_name)
                        data_uuids.append(data_uuid)

                except DataManagerException as err:
                    print("Error registering mosquito result data with data manager, aborting "+err.message)

    else:
        print("Ignore originator with "+originator)
        return

@workflow.handler
def mosquito_shutdown(msg):
    print("\nMosquito simulation shutdown handler")
    IncidentID = msg["IncidentID"]
    workflow.Complete(IncidentID)

# we have to register them with the workflow system
def RegisterHandlers():    
    workflow.RegisterHandler(handler=mosquito_init,        queue="mosquito_init")
    workflow.RegisterHandler(handler=mosquito_postprocess, queue="mosquito_postprocess")
    workflow.RegisterHandler(handler=mosquito_shutdown,    queue="mosquito_shutdown")
    workflow.RegisterHandler(handler=mosquito_test,        queue="mosquito_test")    
