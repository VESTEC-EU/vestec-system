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

static_directory="/lustre/home/dc118/shared/data/moz"

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
def _build_simulation_yaml(species, disease, region, count):
    sample_configuration_file = open("workflows/mosquito/templates/mosquito.yml")
    yaml_template = yaml.load(sample_configuration_file, Loader=yaml.FullLoader)    
    
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
    simulation_yaml=_build_simulation_yaml('albopictus', 'deng', 'trento', 200)
    sim_id=_launch_simulation(IncidentId, "Mosquito simulation", "mosquito_template", "mosquito.yml", simulation_yaml, "mosquito_simulation_postprocess")
    sim_meta = {
        "simulation": sim_id,
        "species": "albopictus",
        "disease": "deng",
        "region": "trento",
        "count": "200"
    }
    workflow.Persist.Put(IncidentId, sim_meta)    

def rome(IncidentId):
    simulation_yaml=_build_simulation_yaml('albopictus', 'deng', 'trento', 200)
    sim_id=_launch_simulation(IncidentId, "Mosquito simulation", "mosquito_template", "mosquito.yml", simulation_yaml, "mosquito_simulation_postprocess")
    sim_meta = {
        "simulation": sim_id,
        "species": "aegypti",
        "disease": "zika",
        "region": "rome",
        "count": "200"
    }
    workflow.Persist.Put(IncidentId, sim_meta)    

def run_simulation_from_payload(IncidentId, config):
    simulation_yaml=_build_simulation_yaml(config["species"], config["disease"], config["region"], int(config["count"]))
    sim_id=_launch_simulation(IncidentId, "Mosquito simulation", "mosquito_template", "mosquito.yml", simulation_yaml, "mosquito_simulation_postprocess")
    sim_meta = {
        "simulation": sim_id,
        "species": config["species"],
        "disease": config["disease"],
        "region": config["region"],
        "count": config["count"]
    }
    workflow.Persist.Put(IncidentId, sim_meta)

@workflow.handler
def mosquito_test(msg):
    print("\nMosquito test handler called to start mosquito simulation")
    IncidentID = msg["IncidentID"]

    try:
        payload = json.loads(msg["data"]["payload"])
        run_simulation_from_payload(IncidentID, payload)
    except KeyError:
        # Run Trento for now
        trento(IncidentID)
 
# mosquito weather init
@workflow.handler
def mosquito_init(msg):
    try:
        registerEndpoint(msg["IncidentID"], "test_stage_"+msg["IncidentID"], "mosquito_test")
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
    
# mosquito simulation postprocessing
@workflow.handler
def mosquito_simulation_postprocess(msg):
    IncidentID = msg["IncidentID"]
    originator = msg['originator']
    logs = workflow.Persist.Get(IncidentID, True)    
    print("\nMosquito simulation postprocess handler", IncidentID)

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
            machine_basedir=simulation.machine.base_work_dir
            if machine_basedir[-1] != "/": machine_basedir+="/"         
        
        if simulation is not None:
            R0_file="R0_"+simulation_metadata["disease"]+".txt"
            if not _check_directory_contains_file(msg["directoryListing"], R0_file):
                print("Result file '"+R0_file+"' not found, exitting")
                return
            convert_yaml=_build_convert_yaml(simulation_metadata["disease"], simulation_metadata["region"], machine_basedir+simulation.directory+"/"+R0_file)
            sim_id=_launch_simulation(IncidentID, "Mosquito conversion", "mosquito_convert_template", "convert.yml", convert_yaml, "mosquito_convert_postprocess")            
            simulation_metadata["simulation"]=sim_id
            workflow.Persist.Put(IncidentID, simulation_metadata)
        else:
            print("No matching simulation record, exitting")
            return

    else:
        print("Ignoring originator with "+originator)
        return

def _build_convert_yaml(disease, region, R0_file):
    sample_configuration_file = open("workflows/mosquito/templates/convert.yml")
    yaml_template = yaml.load(sample_configuration_file, Loader=yaml.FullLoader)    
    
    yaml_template["outbase"]="R0_"+disease
    yaml_template["IDS"]["path"]=static_directory+"/"+region+"/IDS_"+region+".pkl"
    yaml_template["MASCHERA"]["path"]=static_directory+"/"+region+"/MASCHERA_"+region+".pkl"
    yaml_template["C_OUT"]["path"]=R0_file
    return yaml.dump(yaml_template)

# mosquito convert postprocessing
@workflow.handler
def mosquito_convert_postprocess(msg):
    IncidentID = msg["IncidentID"]
    originator = msg['originator']
    logs = workflow.Persist.Get(IncidentID, True)    
    print("\nMosquito convert postprocess handler", IncidentID)
    
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
            R0_file="R0_"+simulation_metadata["disease"]+".tif"
            if not _check_directory_contains_file(msg["directoryListing"], R0_file):
                print("Convert result file '"+R0_file+"' not found, exitting")
                return
            registerMatchingFiles(msg["directoryListing"], ".tif", machine_name, "Mosquito simulation", "application/octet-stream", "Mosquito convert output", 
                simulation.directory, IncidentID, "Mosquito convert output", "Created by convert for mosquito on "+machine_name+" with simulation ID "+simulationId)
            mosaic_yaml=_build_mosaic_yaml(machine_basedir+simulation.directory+"/"+R0_file)
            sim_id=_launch_simulation(IncidentID, "Mosquito mosaic", "mosquito_mosaic_template", "mosaic.yml", mosaic_yaml, "mosquito_mosaic_postprocess")            
            simulation_metadata["simulation"]=sim_id
            workflow.Persist.Put(IncidentID, simulation_metadata)
        else:
            print("No matching simulation record, exitting")
            return

    else:
        print("Ignoring originator with "+originator)
        return

def _build_mosaic_yaml(R0_file):
    sample_configuration_file = open("workflows/mosquito/templates/mosaic.yml")
    yaml_template = yaml.load(sample_configuration_file, Loader=yaml.FullLoader)            
    
    yaml_template["tiffs"][0]["path"]=R0_file
    return yaml.dump(yaml_template)

@workflow.handler
def mosquito_mosaic_postprocess(msg):
    IncidentID = msg["IncidentID"]
    originator = msg['originator']
    logs = workflow.Persist.Get(IncidentID, True)    
    print("\nMosquito mosaic postprocess handler", IncidentID)
    
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
            for i in range(0,12):
                num="0"+str(i) if i<10 else str(i)
                if not _check_directory_contains_file(msg["directoryListing"], "output_band_"+num+".tif"):
                    print("Convert result file 'output_band_"+num+".tif' not found, exitting")
                    return
            # registerMatchingFiles(msg["directoryListing"], ".tif", machine_name, "Mosquito simulation", "application/octet-stream", "Mosquito mosaic output",
            #     simulation.directory, IncidentID, "Mosquito mosaic output", "Created by mosaic for mosquito on "+machine_name+" with simulation ID "+simulationId)
            build_topo_yaml=_build_topo_yaml(simulation_metadata["disease"], simulation_metadata["species"], simulation_metadata["region"], machine_basedir+simulation.directory)
            sim_id=_launch_simulation(IncidentID, "Mosquito topological", "mosquito_topo_template", "topo.yml", build_topo_yaml, "mosquito_topo_postprocess")
            simulation_metadata["simulation"]=sim_id
            workflow.Persist.Put(IncidentID, simulation_metadata)
        else:
            print("No matching simulation record, exitting")
            return

    else:
        print("Ignoring originator with "+originator)
        return

def _build_topo_yaml(disease, species, region, result_dir):
    sample_configuration_file = open("workflows/mosquito/templates/topo.yml")
    yaml_template = yaml.load(sample_configuration_file, Loader=yaml.FullLoader)            
    
    yaml_template["region"]=region
    yaml_template["species"]=species
    yaml_template["disease"]=disease
    for i in range(0,12):
        num="0"+str(i) if i<10 else str(i)        
        yaml_template["tiffs"][i]["path"]=result_dir+"/output_band_"+num+".tif"
    return yaml.dump(yaml_template)        

@workflow.handler
def mosquito_topo_postprocess(msg):
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
def mosquito_shutdown(msg):
    print("\nMosquito simulation shutdown handler")
    IncidentID = msg["IncidentID"]
    workflow.Complete(IncidentID)

# we have to register them with the workflow system
def RegisterHandlers():    
    workflow.RegisterHandler(handler=mosquito_init,        queue="mosquito_init")
    workflow.RegisterHandler(handler=mosquito_simulation_postprocess, queue="mosquito_simulation_postprocess")
    workflow.RegisterHandler(handler=mosquito_convert_postprocess, queue="mosquito_convert_postprocess")
    workflow.RegisterHandler(handler=mosquito_mosaic_postprocess, queue="mosquito_mosaic_postprocess")
    workflow.RegisterHandler(handler=mosquito_topo_postprocess, queue="mosquito_topo_postprocess")    
    workflow.RegisterHandler(handler=mosquito_shutdown,    queue="mosquito_shutdown")
    workflow.RegisterHandler(handler=mosquito_test,        queue="mosquito_test")
