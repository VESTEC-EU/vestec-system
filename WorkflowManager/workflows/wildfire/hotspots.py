import sys
# sys.path.append("../")
# sys.path.append("../../")
from manager import workflow
import os
import uuid
import datetime
import zipfile
import json
import pony.orm as pny
from Database import LocalDataStorage
import geopandas as gpd
import time
from ExternalDataInterface.client import registerEndpoint, ExternalDataInterfaceException, removeEndpoint
from DataManager.client import downloadDataToTargetViaDM, registerDataWithDM, DataManagerException, getLocalFilePathPrepend, putByteDataViaDM, getByteDataViaDM

from Database import Incident


######### ATTENTION #################
#For this to work, you need to have a subdirectory inside WorkflwoManager called `hotspots`
#
# For each incident a directory is created in hotspots. This directory will contain
# - a MODIS directory for MODIS data
# - a VIIRS directory for VIIRS data
# Each sensor's directory will then contain subdirectories for each input data timestamp
# These directories will contain the downloaded satellite data
# The directory structure for an incident is therefore:
#   .
# ├──   MODIS
# │  └──   2020-05-21_144339
# │     
# └──   VIIRS
#    └──   2020-05-21_144900
#      
#
# Presently you run a workflow by executing this file. It will create a new incident, register pull handlers on the EDI and will generate hotspots for the specified region.

#URLS to download the data from
#MODISurl = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/c6/shapes/zips/MODIS_C6_Europe_48h.zip"
MODISurl = "https://vestec.wildfireanalyst.com/static/hotspots/modis_aquaterra_61_firms_nasa_201207_lajonquera.zip"

#VIIRSurl = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/viirs/shapes/zips/VNP14IMGTDL_NRT_Europe_48h.zip"
VIIRSurl = "https://vestec.wildfireanalyst.com/static/hotspots/viirs_suominpp_10nrt_firms_nasa_201207_lajonquera.zip"

hotspotEndpoint="WFAHotspot"

#set the hotspots workdir
#EVENTUALLY THIS SHOULD BE IN A MOUNTED, PERSISTED LOCATION VISIBLE TO ALL CONTAINERS 
wkdir = os.path.abspath("workflows/wildfire/hotspots")

@workflow.handler
def wildfire_hotspot_init_standalone(msg):
    IncidentID = msg["IncidentID"]
    _handle_init(msg)
    workflow.setIncidentActive(IncidentID)

#initialise the workflow
@workflow.handler
def wildfire_hotspot_init(msg):
    _handle_init(msg)

def _handle_init(msg):
    print("\nInitialising hotspot sub-workflow")
    incident = msg["IncidentID"]
    
    #make the working directory for this incident
    os.makedirs(os.path.join(wkdir,incident),exist_ok = True)

    #make sure the coordinates are in the incident DB
    with pny.db_session:
        i = Incident[incident]
        if i.lower_right_latlong == "" or i.upper_left_latlong=="":
            raise ValueError("Region coordinates not provided with incident")

    #register EDI to poll for MODIS data
    try:
        registerEndpoint(incident, MODISurl, "wildfire_modis_newdata", 300)
    except ExternalDataInterfaceException as err:
        print("Failed to register for modis download "+err.message)
        return   

    #register EDI to poll for VIIRS data
    try:
        registerEndpoint(incident, VIIRSurl, "wildfire_viirs_newdata", 300)
    except ExternalDataInterfaceException as err:
        print("Failed to register for VIIRS download "+err.message)
        return    
    
    # register WFA hotspot endpoint
    try:
        registerEndpoint(incident, hotspotEndpoint+"-"+incident, "wildfire_tecnosylva_hotspots")
    except ExternalDataInterfaceException as err:
        print("Failed to register WFA hotspot endpoint "+err.message)
        return

    print("Registered EDI to poll for MODIS, VIIRS, and WFA hotspot data")

@workflow.handler
def wildfire_hotspot_shutdown_standalone(msg):
    IncidentID = msg["IncidentID"]
    _handle_shutdown(IncidentID)
    workflow.Cancel(IncidentID)

@workflow.handler
def wildfire_hotspot_shutdown(msg):
    IncidentID = msg["IncidentID"]
    _handle_shutdown(IncidentID)
    workflow.send(msg, "wildfire_shutdown_response")

def _handle_shutdown(incident):
    try:
        removeEndpoint(incident, MODISurl, "wildfire_modis_newdata", 300)
    except ExternalDataInterfaceException as err:
        print("Failed to remove modis download endpoint "+err.message)   

    #register EDI to poll for VIIRS data
    try:
        removeEndpoint(incident, VIIRSurl, "wildfire_viirs_newdata", 300)
    except ExternalDataInterfaceException as err:
        print("Failed to remove VIIRS download endpoint "+err.message)    
    
    # register WFA hotspot endpoint
    try:
        removeEndpoint(incident, hotspotEndpoint+"-"+incident, "wildfire_tecnosylva_hotspots")
    except ExternalDataInterfaceException as err:
        print("Failed to remove WFA hotspot endpoint "+err.message)

#called when there is new MODIS data
@workflow.handler
def wildfire_modis_newdata(msg):

    incident = msg["IncidentID"]
    header = msg["data"]["headers"]
    modified = header["Last-Modified"]

    #get the things this handler has persisted (list of existing timestamps)  
    persisted = workflow.Persist.Get(incident)
    
    #if the timestamp of this incoming data is not in the persisted data, we download it
    if not check_exists(persisted,modified,type="MODIS"):
        print("\nNew data for MODIS! - %s"%modified)
        
        #create the directory for this timestamp
        datestr = parse_timestamp(modified)
        basedir = os.path.join(wkdir,incident,"MODIS",datestr)

        os.makedirs(getLocalFilePathPrepend()+basedir,exist_ok=True)
        
        #Thefilename (with full path) for the file to be downloaded
        filename = os.path.join(basedir,os.path.basename(MODISurl))

        name = os.path.basename(MODISurl)
        path = basedir
        
        downloadDataToTargetViaDM(filename=name,
                                  path=path,
                                  machine="localhost",
                                  description = "MODIS input datafile for %s"%modified, 
                                  type = "application/zip", 
                                  originator = "hotspot MODIS handler",
                                  url= MODISurl,
                                  protocol = "http",
                                  group = "hotspot",
                                  storage_technology="FILESYSEM",
                                  associate_with_incident=True, 
                                  incidentId=incident)
        
        #unzip it
        unzip(filename, basedir)
                     
        #persist this new timestamp (and the filename)
        d = {
            "modified": modified,
            "filename": filename,
            "type": "MODIS"
        }
        workflow.Persist.Put(incident,d)
        
        #send a message to "process_hotspots" to extract hotspots for the data
        msg = {
            "IncidentID": incident,
            "baseDir": basedir,
            "inputFile": filename,
            "sensor": "MODIS",
            "date": modified
        }
        workflow.send(msg,"wildfire_process_hotspots")
    
   

#called when there is new MODIS data
@workflow.handler
def wildfire_viirs_newdata(msg):

    incident = msg["IncidentID"]
    header = msg["data"]["headers"]
    modified = header["Last-Modified"]

    #get the things this handler has persisted (list of existing timestamps)  
    persisted = workflow.Persist.Get(incident)
    
    #if the timestamp of this incoming data is not in the persisted data, we download it
    if not check_exists(persisted,modified,type="VIIRS"):
        print("\nNew data for VIIRS! - %s"%modified)
        
        #create the directory to download into
        datestr = parse_timestamp(modified)
        basedir = os.path.join(wkdir,incident,"VIIRS",datestr)

        os.makedirs(getLocalFilePathPrepend()+basedir,exist_ok=True)
        
        #get the filename (with full path) for the file to be downloaded
        filename = os.path.join(basedir,os.path.basename(VIIRSurl))

        name = os.path.basename(VIIRSurl)
        path = basedir
        
        downloadDataToTargetViaDM(filename=name,
                                  path=path,
                                  machine="localhost",
                                  description = "VIIRS input datafile for %s"%modified, 
                                  type = "application/zip", 
                                  originator = "hotspot VIIRS handler",
                                  url= VIIRSurl,
                                  protocol = "http",
                                  group = "hotspot",
                                  storage_technology="FILESYSEM",
                                  associate_with_incident=True, 
                                  incidentId=incident)
        
        #unzip it
        unzip(filename, basedir)
                     
        #persist this new timestamp (and the file)
        d = {
            "modified": modified,
            "filename": filename,
            "type": "VIIRS"
        }
        workflow.Persist.Put(incident,d)
        
        #send a message to "process_hotspots" to extract hotspots for the data
        msg = {
            "IncidentID": incident,
            "baseDir": basedir,
            "inputFile": filename,
            "sensor": "VIIRS",
            "date": modified
        }
        workflow.send(msg,"wildfire_process_hotspots")


#Extracts hotspots from the MODIS/VIIRS data
@workflow.handler
def wildfire_process_hotspots(msg):
    incident = msg["IncidentID"]
    inputfile = os.path.splitext(msg["inputFile"])[0]+".shp"
    sensor = msg["sensor"]
    outputdir = os.path.join(msg["baseDir"],"output")
    date = msg["date"]

    print("\nExtracting hotspots from %s"%sensor)
    
    try:
        with pny.db_session:
            i = Incident[incident]
            upperLeft = i.upper_left_latlong
            lowerRight = i.lower_right_latlong
            
            lonmin, latmax = upperLeft.split("/")
            lonmax, latmin = lowerRight.split("/")

            lonmin = float(lonmin)
            latmax = float(latmax)
            lonmax = float(lonmax)
            latmin = float(latmin)
    except Exception as e:
        raise ValueError("Unable to parse region coordinates") from e

    points = [lonmin,latmax,lonmax,latmin]
    
    #extract the hotspots from the data
    hotspots = extract_hotspots(points=points,inputshp = inputfile,sensor = sensor, outputdir=outputdir)

    json_contents=json.dumps(hotspots,indent=1)

    filename = "%s_hotspots.json"%sensor
    path = getLocalFilePathPrepend()+outputdir
    
    #write this json data to the VESTECDB local data storage
    id = putByteDataViaDM(filename = filename, 
                     machine = "localhost", 
                     description = "%s hotspots for region on %s"%(sensor,date), 
                     type = "application/json", 
                     originator = "process hotspots handler", 
                     payload = json_contents.encode("ascii"), 
                     group = "hotspot", 
                     storage_technology="VESTECDB", 
                     path=path, 
                     associate_with_incident=True, 
                     incidentId=incident
                     )

    #clean up files we no longer need (the shape files extracted from the zip)
    removedir = os.path.dirname(inputfile)
    files = os.listdir(getLocalFilePathPrepend()+removedir)
    toremove = []
    for file in files:
        if ".zip" not in file:
            toremove.append(file)
    for file in toremove:
        print("Deleting %s"%file)
        os.remove(os.path.join(getLocalFilePathPrepend()+removedir,file))

    outfile = os.path.join(path,filename)

    message = {
        "IncidentID": incident,
        "file": outfile,
        "file_id": id,
        "date": date
    }

    workflow.send(message,"wildfire_consolidate_hotspots")

@workflow.atomic
@workflow.handler
def wildfire_consolidate_hotspots(msg):
    incident = msg["IncidentID"]
    hotspotsfile = msg["file"]
    date = msg["date"]
    file_id = msg["file_id"]
    
    #Get the data from the new hotspots file from the DM
    json_data = getByteDataViaDM(file_id).decode("ascii")
    newhotspots = json.loads(json_data)
    
    consolidated = workflow.Persist.Get(incident)
    
    #get the latest consolidated hotspot data from the DM
    if len(consolidated) != 0:
        fid = consolidated[-1]["file_id"]
        json_data = getByteDataViaDM(fid).decode("ascii")
        hotspots = json.loads(json_data)
        

    #no existing hotspot data
    if len(consolidated) == 0:
        #hotspotsfile is the consolidated list
        hotspots = {"type":newhotspots["type"],"crs": newhotspots["crs"], "features": []}
    
    #add new hotspots if they aren't already in the hotspots list
    added = 0
    for hotspot in newhotspots["features"]:
        if hotspot not in hotspots["features"]:
            hotspots["features"].append(hotspot)
            added +=1
    
    if added > 0:

        #we have new data. Write a new json

        timestamp = parse_timestamp(date)

        basedir = os.path.join(wkdir,incident,"consolidated",timestamp)

        file = os.path.join(basedir,"hotspots.json")

        contents = json.dumps(hotspots,indent=1)

        #store the new consolidated hotspots in the database
        id = putByteDataViaDM(filename = "hotspots.json", 
                     path=basedir, 
                     machine = "localhost", 
                     description = "Consolidated hotspots for region on %s"%(date), 
                     type = "application/json", 
                     originator = "consolidate hotspots handler", 
                     payload = contents.encode("ascii"), 
                     group = "hotspot", 
                     storage_technology="VESTECDB", 
                     associate_with_incident=True, 
                     incidentId=incident
                     )

        
        nhot = len(hotspots["features"])

        print("\nConsolidate hotspots: Created new consolidated hotspots file for %s with %d new hotspots, %d total"%(date,added,nhot))

        workflow.Persist.Put(incident,{"file": file, "date": date, "file_id": id})

    else:
        print("\nConsolidate hotspots: No new hotspots")
        


def check_exists(persisted,modified,type):
    for p in persisted:
        if p["modified"] == modified and p["type"]==type:
            return True
    return False

def unzip(target,dir):
    print("Unzipping %s"%target)
    file = zipfile.ZipFile(getLocalFilePathPrepend()+target, 'r')
    file.extractall(getLocalFilePathPrepend()+dir)
    file.close()

def zip(files,target):
    print("Zipping %s"%target)
    file = zipfile.ZipFile(getLocalFilePathPrepend()+target, "w")
    for f in files:
        file.write(getLocalFilePathPrepend()+f)
    file.close()
 

#from a MODIS/VIIRS "modified" timestamp, produce a more 'friendly' datestring
def parse_timestamp(datestr):
    date=datetime.datetime.strptime(datestr,"%a, %d %b %Y %H:%M:%S %Z")
    newstring = date.strftime("%Y-%m-%d_%H%M%S")
    return newstring

def convert_to_geojson(input_shapefile_path, output_geojson_path):
    """ Creates a GeoJSON file from an existent Shapefile with the same name.
    Given a shapefile path, creates it's GeoJSON version and writes it to the disk
    with the path and name of the given output_geojson_path (e.g 'test/new_geojson.geojson)

    Args:
        input_shapefile_path (str): The path of the input shapefile. The
                                    new file will be created in the same path.
        output_geojson_path (str): The path of the ouput GeoJSON.
    """
    print("Creating geojson from %s"%os.path.basename(input_shapefile_path))
    current_shape = gpd.read_file(getLocalFilePathPrepend()+input_shapefile_path)
    current_shape.to_file(getLocalFilePathPrepend()+output_geojson_path, driver="GeoJSON")

#extracts hotspots found in the satellite data shapefile form sensor within points. 
def extract_hotspots(points, inputshp, sensor, outputdir):
    dir = os.path.dirname(inputshp)
    basename = os.path.basename(inputshp)
    name, ext = os.path.splitext(basename)
    inputjson = name + ".json"
    inputjson = os.path.join(dir,inputjson)
    convert_to_geojson(inputshp, inputjson)

    f = open(getLocalFilePathPrepend()+inputjson,"r")
    data = json.load(f)
    f.close()

    hotspots = []

    print("Looking for hotspots in %s"%os.path.basename(inputjson))

    for feature in data["features"]:
        if feature["geometry"]["type"] == "Point":
            coords = feature["geometry"]["coordinates"]
            #check that the feature is within the geagraphical range described by points
            if (coords[0] >= points[0] and coords[0] <= points[2]):
                if (coords[1] >= points[3] and coords[1] <= points[1]):
                    
                    #now check that the condifence is high enough
                    confidence = feature["properties"]["CONFIDENCE"]
                    if sensor == "MODIS": #MODIS
                        if confidence < 50:
                            continue
                    elif sensor == "VIIRS":
                        if confidence == "low": #VIIRS
                            continue
                    else:
                        raise ValueError("Unknown Sensor")
                    #create the dict for this hotspot
                    d={}
                    FRP = feature["properties"]["FRP"]
                    DATE = feature["properties"]["ACQ_DATE"]
                    TIME = feature["properties"]["ACQ_TIME"]

                    d["type"] =  "Feature"
                    d["properties"] = {
                                        "FRP": FRP,
                                        "DATE": DATE,
                                        "TIME": TIME,
                                        "SENSOR": sensor
                                       }
                    d["geometry"] = feature["geometry"]

                    hotspots.append(d)


    print("Found %d hotspots"%len(hotspots))

    d = {}
    d["type"] = "FeatureCollection"
    d["crs"] = data["crs"]
    d["features"] = hotspots
    
    #delete the input json file (no longer needed)
    os.remove(getLocalFilePathPrepend()+inputjson)

    return d


@workflow.handler
def wildfire_tecnosylva_hotspots(msg):
    print("\nHotspot data incoming from Tecnosylva")    

    provided_hotspot_data=json.loads(msg["data"]["payload"])
    
    incidentId=provided_hotspot_data["incidentID"]
    payload=provided_hotspot_data["payload"]       

    try:
        data_uuid=registerDataWithDM("WFA_hotspots.json", "localhost", "WFA", "application/json", str(len(payload)), "WFA hotspot data", 
                storage_technology="VESTECDB", path=incidentId, associate_with_incident=True, incidentId=incidentId, kind="WFA provided hotspot data", 
                comment="WFA provided hotspot data")
    except DataManagerException as err:
        print("Error registering hotspot data with DM, "+err.message)
        return

    with pny.db_session:
        new_file = LocalDataStorage(contents=payload.encode("ascii"), filename=incidentId+"/WFA_hotspots.json", filetype="WFA provided hotspot data") 

    print("Hotspot data stored")

    fwdmsg={"IncidentID" : incidentId, "hotspot_data_uuid" : data_uuid}
    workflow.send(fwdmsg,"wildfire_fire_simulation")

#register the handlers with the workflow system
def RegisterHandlers():
    workflow.RegisterHandler(wildfire_hotspot_init, "wildfire_hotspot_init")
    workflow.RegisterHandler(wildfire_hotspot_init_standalone, "wildfire_hotspot_init_standalone")
    workflow.RegisterHandler(wildfire_hotspot_shutdown, "wildfire_hotspot_shutdown")
    workflow.RegisterHandler(wildfire_hotspot_shutdown_standalone, "wildfire_hotspot_shutdown_standalone")
    workflow.RegisterHandler(wildfire_modis_newdata, "wildfire_modis_newdata")
    workflow.RegisterHandler(wildfire_viirs_newdata, "wildfire_viirs_newdata")
    workflow.RegisterHandler(wildfire_process_hotspots, "wildfire_process_hotspots")
    workflow.RegisterHandler(wildfire_tecnosylva_hotspots,"wildfire_tecnosylva_hotspots")
    workflow.RegisterHandler(wildfire_consolidate_hotspots,"wildfire_consolidate_hotspots")


