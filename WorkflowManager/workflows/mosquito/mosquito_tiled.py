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
def _launch_simulation(IncidentID, simulation_description, template_directory, yaml_filename, yaml_configuration, callback):
    try:
        callbacks = { 'COMPLETED': callback }
        # ./R0 -a trento -s albopictus -d deng -ns 200 -rt n
        sim_id = createSimulation(IncidentID, 1, "00:15:00", simulation_description, "submit.sh", callbacks, template_dir="templates/"+template_directory)[0]
        with pny.db_session:
            simulation=Simulation[sim_id]    
            machine_name=simulation.machine.machine_name            

        try:                
            putByteDataViaDM(yaml_filename, machine_name, simulation_description+" configuration", "text/plain", "Mosquito workflow", yaml_configuration, path=simulation.directory)                 
        except DataManagerException as err:
            print("Can not write "+simulation_description+" configuration to simulation location"+err.message)        

        submitSimulation(sim_id)
        return sim_id
    except SimulationManagerException as err:
        print("Error creating or submitting simulation "+err.message)
        return

@pny.db_session
def _build_simulation_yaml(species, disease, count, lat_first_point, lon_first_point, lat_second_point, lon_second_point, n_max_tiles):
    sample_configuration_file = open("workflows/mosquito/templates/tiled-template.yml")
    yaml_template = yaml.load(sample_configuration_file, Loader=yaml.FullLoader)    
    
    yaml_template["species"]=species
    yaml_template["disease"]=disease
    yaml_template["count"]=count

    yaml_template["species_user_parameters"]["path"]="${MOSQUITO_INSTALL_DIR}/share/mosquito/input_files/"+species+"_parameter.txt"
    yaml_template["species_fixed_parameters"]["path"]="${MOSQUITO_INSTALL_DIR}/share/mosquito/input_files/"+species+"_parameter_fixed.txt"
    yaml_template["species_alpha_distribution"]["path"]="${MOSQUITO_INSTALL_DIR}/share/mosquito/input_files/"+species+"_alpha_w_k_m_wc_lm_within_fit_cumulato_best_dic.txt"
    yaml_template["species_covariate_distribution"]["path"]="${MOSQUITO_INSTALL_DIR}/share/mosquito/input_files/"+species+"_coeff_covariate_wc_lm_within_fit_cumulato_best_dic.txt"
    yaml_template["disease_species_user_parameters"]["path"]="${MOSQUITO_INSTALL_DIR}/share/mosquito/input_files/"+disease+"_"+species+"_parameter_user.txt"    
        
    return yaml.dump(yaml_template)

def testRun(IncidentId):
    simulation_yaml=_build_simulation_yaml('albopictus', 'chik', 200, 41, 12, 42, 13, 4)
    sim_id=_launch_simulation(IncidentId, "Mosquito simulation", "mosquito_tiled_template", "tiled-template.yml", simulation_yaml, "mosquito_tiled_simulation_completed")
    sim_meta = {
        "simulation": sim_id,
        "species": "albopictus",
        "disease": "chik",
        "count": "200"
    }
    workflow.Persist.Put(IncidentId, sim_meta)    

def run_simulation_from_payload(IncidentId, config):
    simulation_yaml=_build_simulation_yaml(config["species"], config["disease"], int(config["count"]), int(config["lat_first_point"]), int(config["lon_first_point"]), int(config["lat_second_point"]), int(config["lon_second_point"]), int(config["n_max_tiles"]))
    sim_id=_launch_simulation(IncidentId, "Mosquito simulation", "mosquito_tiled_template", "tiled-template.yml", simulation_yaml, "mosquito_tiled_simulation_completed")
    sim_meta = {
        "simulation": sim_id,
        "species": config["species"],
        "disease": config["disease"],
        "count": config["count"]
    }
    workflow.Persist.Put(IncidentId, sim_meta)

@workflow.handler
def mosquito_tiled_test(msg):
    print("\nMosquito tiled test handler called to start mosquito simulation")
    IncidentID = msg["IncidentID"]

    try:
        payload = json.loads(msg["data"]["payload"])
        run_simulation_from_payload(IncidentID, payload)
    except KeyError:
        # Run Trento for now
        testRun(IncidentID)
 
# mosquito weather init
@workflow.handler
def mosquito_tiled_init(msg):
    try:
        registerEndpoint(msg["IncidentID"], "test_stage_"+msg["IncidentID"], "mosquito_tiled_test")
    except ExternalDataInterfaceException as err:
        print("Error from EDI on registration "+err.message)

    workflow.setIncidentActive(msg["IncidentID"])

def _retrieve_simulation_metadata(meta_infos, simulationId):    
    for meta in meta_infos:        
        if meta["simulation"] == simulationId:
            return meta
    raise Exception

def _check_directory_contains_file(directoryListing, filename):
    for entry in directoryListing:
        tokens=entry.split()
        if filename == tokens[-1]:
            return True
    return False
    
@workflow.handler
def mosquito_tiled_simulation_completed(msg):
    IncidentID = msg["IncidentID"]
    originator = msg['originator']
    logs = workflow.Persist.Get(IncidentID, True)    
    print("\nMosquito simulation completed, running post process for ", IncidentID)
    
    if originator == 'Simulation Completed':
        simulationId = msg["simulationId"]
        try:
            simulation_metadata=_retrieve_simulation_metadata(workflow.Persist.Get(IncidentID, True), simulationId)
        except Exception:
            print("No metadata for simulation "+simulationId)
            return

        with pny.db_session:
            myincident = Incident[IncidentID]
            simulation=Simulation[simulationId]
            machine_name=simulation.machine.machine_name
            machine_basedir=simulation.machine.base_work_dir
            if machine_basedir[-1] != "/": machine_basedir+="/"         
        
        if simulation is not None:
            registerMatchingFiles(msg["directoryListing"], ".tif", machine_name, "Mosquito simulation", "application/octet-stream", "Mosquito simulation output",
                simulation.directory, IncidentID, "Mosquito simulation output", "Created by mosquito simulation on "+machine_name+" with simulation ID "+simulationId)
            
            if not _check_directory_contains_file(msg["directoryListing"], "output_area.tif"):
                print("Can not fine output_area.tif from the simulation run, this is needed!")
                return

            build_topo_yaml=_build_topo_yaml(simulation_metadata["disease"], simulation_metadata["species"], machine_basedir+simulation.directory, msg["directoryListing"])
            sim_id=_launch_simulation(IncidentID, "Mosquito topological", "mosquito_topo_template", "topo.yml", build_topo_yaml, "mosquito_tiled_topo_postprocess")
            simulation_metadata["simulation"]=sim_id
            workflow.Persist.Put(IncidentID, simulation_metadata)
        else:
            print("No matching simulation record, exiting")
            return

    else:
        print("Ignoring originator with "+originator)
        return

def _build_topo_yaml(disease, species, result_dir, directoryListing):
    sample_configuration_file = open("workflows/mosquito/templates/topo-tiled.yml")
    yaml_template = yaml.load(sample_configuration_file, Loader=yaml.FullLoader)            
    
    yaml_template["species"]=species
    yaml_template["disease"]=disease    
    for i in range(0,12):
        if _check_directory_contains_file(directoryListing, "output_area_band_"+str(i)+".tif"):
           yaml_template["inputs"][i]["path"]=result_dir+"/output_area_band_"+str(i)+".tif"
        else:
           print("Error - can not find file 'output_area_band_"+str(i)+".tif' I continue but probably won't work!")
    return yaml.dump(yaml_template)        

@workflow.handler
def mosquito_tiled_topo_postprocess(msg):
    IncidentID = msg["IncidentID"]
    originator = msg['originator']
    logs = workflow.Persist.Get(IncidentID)
    print("\nMosquito topo postprocess handler", IncidentID)

    if originator == 'Simulation Completed':
        simulationId = msg["simulationId"]
        simulationIdPostfix=simulationId.split("-")[-1]              

        with pny.db_session:
            myincident = Incident[IncidentID]
            simulation=Simulation[simulationId]
            machine_name=simulation.machine.machine_name                     

        if simulation is not None:
            registerMatchingFiles(msg["directoryListing"], ".zip", machine_name, "Mosquito simulation", "application/zip", "Mosquito topological output", 
                simulation.directory, IncidentID, "Mosquito topological output", "Created by ttk for mosquito on "+machine_name+" with simulation ID "+simulationId)            
    else:
        print("Ignoring originator with "+originator)
        return

def registerMatchingFiles(directoryListing, matching_ending, machine_name, source, meta_file_description, description, directory, IncidentID, kind_description, commentStr):
    for entry in directoryListing:
        tokens=entry.split()
        if len(tokens) == 9 and matching_ending in tokens[-1]:
            if tokens[4].isnumeric():
                file_size=int(tokens[4])
            else:
                file_size=0
            try:
                registerDataWithDM(tokens[-1], machine_name, source, meta_file_description, file_size, description, 
                    path=directory, associate_with_incident=True, incidentId=IncidentID, kind=kind_description, 
                    comment=commentStr)
            except DataManagerException as err:
                print("Error registering "+description+" with data manager, aborting "+err.message)
                return            

@workflow.handler
def mosquito_tiled_shutdown(msg):
    print("\nMosquito simulation shutdown handler")
    IncidentID = msg["IncidentID"]
    workflow.Complete(IncidentID)

# we have to register them with the workflow system
def RegisterHandlers():    
    workflow.RegisterHandler(handler=mosquito_tiled_init,        queue="mosquito_tiled_init")
    workflow.RegisterHandler(handler=mosquito_tiled_simulation_completed, queue="mosquito_tiled_simulation_completed")
    workflow.RegisterHandler(handler=mosquito_tiled_topo_postprocess, queue="mosquito_tiled_topo_postprocess")    
    workflow.RegisterHandler(handler=mosquito_tiled_shutdown,    queue="mosquito_tiled_shutdown")
    workflow.RegisterHandler(handler=mosquito_tiled_test,        queue="mosquito_tiled_test")
