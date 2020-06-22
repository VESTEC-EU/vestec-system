import workflow
import requests
import os
os.path.join("../")
import hashlib
import uuid
import datetime
import zipfile
import json
import pony.orm as pny
from Database import LocalDataStorage
import geopandas as gpd

from Database import Incident


######### ATTENTION #################
#For this to work, you need to have a subdirectory inside WorkflwoManager called `hotspots`
#
# For each incident a directory is in hotspots. This directory will contain
# - a MODIS directory for MODIS data
# - a VIIRS directory for VIIRS data
# Each sensor's directory will then contain subdirectories for each input data timestamp
# These subdirectories will contain an input and output directory with the shape file
# downloaded from the internet in input, and the geojson in the output
# The directory structure for an incident is therefore:
#   .
# ├──   MODIS
# │  └──   2020-05-21_144339
# │     ├──   input
# │     │  └──   MODIS_C6_Europe_48h.zip
# │     └──   output
# │        └──   MODIS_hotspots.json
# │        
# └──   VIIRS
#    └──   2020-05-21_144900
#       ├──   input
#       │  └──   VNP14IMGTDL_NRT_Europe_48h.zip
#       └──   output
#          └──   VIIRS_hotspots.json
#
# Presently you run a workflow by executing this file. It will create a new incident, register pull handlers on the EDI and will generate hotspots for the specified region.


if "VESTEC_SM_URI" in os.environ:
    SM_URL= os.environ["VESTEC_SM_URI"]
else:
    SM_URL = 'http://localhost:5505/SM'

if "VESTEC_EDI_URI" in os.environ:
    EDI_URL = os.environ["VESTEC_EDI_URI"]
else:
    EDI_URL= 'http://localhost:5501/EDImanager'

if "VESTEC_DM_URI" in os.environ:
    DATA_MANAGER_URL = os.environ["VESTEC_DM_URI"]
else:
    DATA_MANAGER_URL = 'http://localhost:5000/DM'

#URLS to download the data from
MODISurl = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/c6/shapes/zips/MODIS_C6_Europe_48h.zip"

VIIRSurl = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/viirs/shapes/zips/VNP14IMGTDL_NRT_Europe_48h.zip"


#set up the hotspots workdir
wkdir = os.path.abspath("hotspots")


#initialise the workflow
@workflow.handler
def init(msg):
    incident = msg["IncidentID"]
    
    #make the working directory for this incident
    os.mkdir(os.path.join(wkdir,incident))

    #make sure the coordinates are in the incident DB
    with pny.db_session:
        i = Incident[incident]
        if i.lower_right_latlong == "" or i.upper_left_latlong=="":
            raise ValueError("Region coordinates not provided with incident")

    workflow.setIncidentActive(incident)
    
    #register EDI to poll for MODIS data
    myobj = {
        'queuename': 'modis_newdata',
        'incidentid': incident, 
        'endpoint': MODISurl,
        "pollperiod": 300
            }
    x = requests.post(EDI_URL+"/register", json = myobj)
    print("EDI response for MODIS data arrival" + x.text)

    if x.status_code != 200:
        raise Exception("Failed to register for modis download")
    
    #register EDI to poll for VIIRS data
    myobj = {
        'queuename': 'viirs_newdata',
        'incidentid': incident, 
        'endpoint': VIIRSurl,
        "pollperiod": 300
            }
    x = requests.post(EDI_URL+"/register", json = myobj)
    print("EDI response for VIIRS data arrival" + x.text)

    if x.status_code != 200:
        raise Exception("Failed to register for modis download")
    
    print("Ready to go :)\n")



#called when there is new MODIS data
@workflow.handler
def newMODISdata(msg):

    incident = msg["IncidentID"]
    header = msg["data"]["headers"]
    modified = header["Last-Modified"]

    #get the things this handler has persisted (list of existing timestamps)  
    persisted = workflow.Persist.Get(incident)
    
    #if the timestamp of this incoming data is not in the persisted data, we download it
    if not check_exists(persisted,modified,type="MODIS"):
        print("\nnew data for MODIS! - %s"%modified)
        
        #create the needed directories
        datestr = parse_timestamp(modified)
        
        basedir = os.path.join(wkdir,incident,"MODIS",datestr)
        filedir = os.path.join(basedir,"input")

        os.makedirs(filedir,exist_ok=True)
        
        #select the filename (with full path) for the file to be downloaded
        filename = os.path.join(filedir,os.path.basename(MODISurl))
        
        #instruct its download
        dm_download(file = filename,
                    machine = "localhost",
                    description = "MODIS input datafile for %s"%modified,
                    originator = "hotspot MODIS hadler",
                    group = "hotspot",
                    url = MODISurl,
                    incident = incident)
        
        #unzip it
        unzip(filename,filedir)
                     
        
        #persist this new timestamp (and the file)
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
            "regionFile": os.path.join(wkdir,incident,"region","northern_italy.shp"),
            "date": modified
        }
        workflow.send(msg,"process_hotspots")
    
   

#called when there is new MODIS data
@workflow.handler
def newVIIRSdata(msg):

    incident = msg["IncidentID"]
    header = msg["data"]["headers"]
    modified = header["Last-Modified"]

    #get the things this handler has persisted (list of existing timestamps)  
    persisted = workflow.Persist.Get(incident)
    
    #if the timestamp of this incoming data is not in the persisted data, we download it
    if not check_exists(persisted,modified,type="VIIRS"):
        print("\nnew data for VIIRS! - %s"%modified)
        
        #create the needed directories
        datestr = parse_timestamp(modified)
        
        basedir = os.path.join(wkdir,incident,"VIIRS",datestr)
        filedir = os.path.join(basedir,"input")

        os.makedirs(filedir,exist_ok=True)
        
        #select the filename (with full path) for the file to be downloaded
        filename = os.path.join(filedir,os.path.basename(VIIRSurl))
        
        #instruct its download
        dm_download(file = filename,
                    machine = "localhost",
                    description = "VIIRS input datafile for %s"%modified,
                    originator = "hotspot VIIRS hadler",
                    group = "hotspot",
                    url = VIIRSurl,
                    incident = incident)
        
        #unzip it
        unzip(filename,filedir)
                     
        
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
            "regionFile": os.path.join(wkdir,incident,"region","northern_italy.shp"),
            "date": modified
        }
        workflow.send(msg,"process_hotspots")


#Extracts hotspots from the MODIS/VIIRS data
@workflow.handler
def process_hotspots(msg):
    incident = msg["IncidentID"]
    inputfile = os.path.splitext(msg["inputFile"])[0]+".shp"
    sensor = msg["sensor"]
    outputdir = os.path.join(msg["baseDir"],"output")
    date = msg["date"]
    
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

    
    #This needs to be taken from the Incident table in the DB eventually
    # print(points)
    # print([1.8347167968750002, 53.38332836757156, 11.744384765625, 48.75618876280552])
    #points = [1.8347167968750002, 53.38332836757156, 11.744384765625, 48.75618876280552]
    
    #make the directry to place the hotspots files
    os.mkdir(outputdir)

    print("\n")

    outfile = extract_hotspots(points=points,inputshp = inputfile,sensor = sensor, outputdir=outputdir)

    dm_register(file=outfile,
                machine="localhost",
                description = "%s hotspots for region on %s"%(sensor,date),
                originator = "process hotspots handler",
                group = "hotspot",
                storage_technology= "VESTECDB",
                incident = incident)

    #clean up files we no longer need
    removedir = os.path.dirname(inputfile)
    files = os.listdir(removedir)
    toremove = []
    for file in files:
        if ".zip" not in file:
            toremove.append(file)
    for file in toremove:
        print("Deleting %s"%file)
        os.remove(os.path.join(removedir,file))



def check_exists(persisted,modified,type):
    for p in persisted:
        if p["modified"] == modified and p["type"]==type:
            return True
    return False

def unzip(target,dir):
    print("Unzipping %s"%target)
    file = zipfile.ZipFile(target, 'r')
    file.extractall(dir)
    file.close()

def zip(files,target):
    print("Zipping %s"%target)
    file = zipfile.ZipFile(target, "w")
    for f in files:
        file.write(f)
    file.close()

#register a file with the DM
def dm_register(file,machine,description,originator,group, incident, storage_technology):
    print("Registering %s with DataManager"%file)
    path, filename = os.path.split(file)
    size = os.path.getsize(file)

    data = {
        "filename": filename,
        "path": path,
        "machine": machine,
        "size": size,
        "description": description,
        "originator": originator,
        "group": group,
        "storage_technology": storage_technology
    }
    r = requests.put(os.path.join(DATA_MANAGER_URL,"register"),data=data)
    if r.status_code != 201:
        print("ERROR! %s"%r.text)
        raise Exception("DM could not register file")

    with pny.db_session:
        I = Incident[incident]
        I.associated_datasets.create(
            uuid=r.text,
            name=file, 
            type=group, 
            comment=description,         
            date_created=datetime.datetime.now()
        )
    return    

#download a file with the DM
def dm_download(file,machine,description,originator,group,url,incident):
    print("Asking dm to download %s"%url)
    path, filename = os.path.split(file)


    data ={
        "filename": filename,
        "path": path,
        "machine": machine,
        "description": description,
        "originator": originator,
        "group": group,
        "url": url,
        "protocol": "http",
        "options": json.dumps({})
    }

    r = requests.put(os.path.join(DATA_MANAGER_URL,"getexternal"),data=data)

    if r.status_code != 201:
        print("ERROR! %s"%r.text)
        raise Exception("DM could not download file")

    with pny.db_session:
        I = Incident[incident]
        I.associated_datasets.create(
            uuid=r.text,
            name=file, 
            type=group, 
            comment=description,         
            date_created=datetime.datetime.now()
        )
    return    

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
    current_shape = gpd.read_file(input_shapefile_path)
    current_shape.to_file(output_geojson_path, driver="GeoJSON")

#extracts hotspots found in the satellite data shapefile form sensor within points. 
def extract_hotspots(points, inputshp, sensor, outputdir):
    dir = os.path.dirname(inputshp)
    basename = os.path.basename(inputshp)
    name, ext = os.path.splitext(basename)
    inputjson = name + ".json"
    inputjson = os.path.join(dir,inputjson)
    convert_to_geojson(inputshp,inputjson)
    f = open(inputjson,"r")
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
                                        "TIME": TIME
                                       }
                    d["geometry"] = feature["geometry"]

                    hotspots.append(d)


    print("Found %d hotspots"%len(hotspots))

    d = {}
    d["type"] = "FeatureCollection"
    d["crs"] = data["crs"]
    d["features"] = hotspots

    outfile = os.path.join(outputdir,"%s_hotspots.json"%sensor)
    
    contents=json.dumps(d,indent=1)
    with pny.db_session:
        new_file = LocalDataStorage(contents=contents, filename=outfile, filetype="application/json")    
    
    #delete the input json file (no longer needed)
    os.remove(inputjson)

    return outfile

    

#register the handlers with the workflow system
def RegisterHandlers():
    workflow.RegisterHandler(init, "hotspot_init")
    workflow.RegisterHandler(newMODISdata, "modis_newdata")
    workflow.RegisterHandler(newVIIRSdata, "viirs_newdata")
    workflow.RegisterHandler(process_hotspots, "process_hotspots")



#kick off an incident for the hotspot workflow
if __name__ == "__main__":
    upperLeft = "1.8347167968750002/53.38332836757156"
    lowerRight = "11.744384765625/48.75618876280552"
    incident = workflow.CreateIncident("hotspot", "test_hotspot",upper_left_latlong=upperLeft,lower_right_latlong=lowerRight)

    workflow.OpenConnection()
    workflow.send({"IncidentID": incident},"hotspot_init")
    workflow.FlushMessages()
    workflow.CloseConnection()



    



