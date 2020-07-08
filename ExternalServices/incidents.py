from WorkflowManager import workflow
from Database.users import User
from Database.workflow import Incident, RegisteredWorkflow, MessageLog, StoredDataset
from Database.DataManager import DataTransfer
import pony.orm as pny
from flask import jsonify
from flask_jwt_extended import get_jwt_identity
from functools import wraps
import networkx as nx
from networkx.drawing.nx_agraph import to_agraph
import datetime
from operator import itemgetter
import sys
sys.path.append("../")
from DataManager.client import getInfoForDataInDM, DataManagerException


def checkIfUserCanAccessIncident(incident, user):
    if (incident is not None and user is not None):
        if (incident.user_id.user_id==user.user_id):
            return True
    return False

@pny.db_session
def createIncident(incident_name, incident_kind, username, incident_upper_left_latlong="", incident_lower_right_latlong="", duration=None):
    user_id = User.get(username=username)
    if duration is not None:
        job_id = workflow.CreateIncident(incident_name, incident_kind, user_id=user_id, upper_left_latlong=incident_upper_left_latlong, lower_right_latlong=incident_lower_right_latlong, duration=duration)
    else:
        job_id = workflow.CreateIncident(incident_name, incident_kind, user_id=user_id, upper_left_latlong=incident_upper_left_latlong, lower_right_latlong=incident_lower_right_latlong)

    return job_id

def generateIncidentDiGraph(incident_uuid):
    #directional graph structure to store the graph
    G=nx.DiGraph()

    with pny.db_session:
        messages = pny.select(m for m in MessageLog if m.incident_id == incident_uuid)[:]

        for m in messages:
            originator = m.originator
            destination = m.destination
            
            #remove handler or queue suffixes from names if present (just for cosmetic reasons)
            originator= originator.replace("_handler","")
            destination = destination.replace("_queue","")
            
            #if the src and dest tags are present, use these as node names instead of the originator and destination fields
            if m.src_tag != "":
                originator = m.src_tag
            if m.dest_tag != "":
                destination = m.dest_tag
            
            #don't display any handlers internal to the workflow system
            if originator[0] == "_":
                continue
            
            #create nodes and join them together
            G.add_node(originator,style="filled",fillcolor="chartreuse") #originator clearly called successfully
            
            if m.status == "SENT":
                colour="white"
            elif m.status == "COMPLETE":
                colour = "chartreuse"
            elif m.status == "PROCESSING":
                colour = "orange"
            elif m.status == "ERROR":
                colour = "red"
            else:
                colour = "grey"
            tooltip_msg="Status of "+m.status
            if m.date_received is None and m.date_completed is None:
                tooltip_msg+=", message sent to state on "+m.date_submitted.strftime("%d/%m/%Y, %H:%M:%S")
            elif m.date_completed is None:
                tooltip_msg+=", message received and stage started on "+m.date_received.strftime("%d/%m/%Y, %H:%M:%S")
            else:
                tooltip_msg+=", stage completed on "+m.date_completed.strftime("%d/%m/%Y, %H:%M:%S")            

            G.add_node(destination,style="filled",fillcolor=colour, tooltip=tooltip_msg)
            G.add_edge(originator,destination)
    return to_agraph(G)

def packageSimulation(sim):
    simulation_dict={}
    simulation_dict["uuid"]=sim.uuid
    if sim.jobID is not None and sim.jobID != "":
        simulation_dict["jobID"]=sim.jobID        

    simulation_dict["status"]=sim.status
    simulation_dict["status_updated"]=sim.status_updated.strftime("%d/%m/%Y, %H:%M:%S")

    if sim.status_message is not None and sim.status_message != "":
        simulation_dict["status_message"]=sim.status_message
                
    simulation_dict["created"]=sim.date_created.strftime("%d/%m/%Y, %H:%M:%S")
    simulation_dict["walltime"]=sim.walltime
    simulation_dict["kind"]=sim.kind
    simulation_dict["num_nodes"]=sim.num_nodes
    simulation_dict["requested_walltime"]=sim.requested_walltime
    if sim.machine is not None:
        simulation_dict["machine"]=sim.machine.machine_name
    return simulation_dict

def packageDataset(stored_ds):
    stored_ds_dict={}
    stored_ds_dict["uuid"]=stored_ds.uuid
    stored_ds_dict["name"]=stored_ds.name
    stored_ds_dict["type"]=stored_ds.type
    stored_ds_dict["comment"]=stored_ds.comment
    stored_ds_dict["date_created"]=stored_ds.date_created.strftime("%d/%m/%Y, %H:%M:%S")
    try:
        data_info=getInfoForDataInDM(stored_ds.uuid)                
        stored_ds_dict["machine"]=data_info["machine"]
    except DataManagerException as err:
        print("Can not retrive data info from DM "+err.message)
        stored_ds_dict["machine"]=""
    return stored_ds_dict

def packageDataTransfer(data_transfer):
    dt_dict = {}

    dt_dict["filename"] = data_transfer.src.name
    dt_dict["src_machine"] = data_transfer.src_machine
    dt_dict["dst_machine"] = data_transfer.dst_machine
    dt_dict["date_started"] = data_transfer.date_started
    dt_dict["date_completed"] = data_transfer.date_completed
    dt_dict["completion_time"] = data_transfer.completion_time
    dt_dict["status"] = data_transfer.status

    return dt_dict

@pny.db_session
def packageAllDataTransfersForDatasets(associated_datasets):
    ds_ids = list(ds.uuid for ds in associated_datasets)

    data_transfers = pny.select(dt for dt in DataTransfer
                                if dt.src.id in ds_ids
                                or dt.dst.id in ds_ids)[:]

    return list(packageDataTransfer(dt) for dt in data_transfers)

def packageIncident(stored_incident, include_sort_key, include_digraph, include_manual_data_queuename, include_associated_data, include_associated_simulations, include_associated_data_transfers):
    incident={}
    incident["uuid"]=stored_incident.uuid
    incident["kind"]=stored_incident.kind
    incident["name"]=stored_incident.name
    incident["status"]=stored_incident.status
    incident["comment"]=stored_incident.comment         
    incident["creator"]=stored_incident.user_id.username
    if stored_incident.duration is not None:
        incident["duration"]=stored_incident.duration
    incident["date_started"]=stored_incident.date_started.strftime("%d/%m/%Y, %H:%M:%S")    
    
    incident_workflow=RegisteredWorkflow.get(kind=stored_incident.kind)
    if incident_workflow is not None:
        incident["test_workflow"]=incident_workflow.test_workflow

    if include_associated_simulations:
        incident["simulations"]=[]
        for sim in stored_incident.simulations:                                   
            incident["simulations"].append(packageSimulation(sim))

        incident["simulations"]=sorted(incident["simulations"], key=itemgetter('created'), reverse=True)

    if (stored_incident.date_completed is not None):
        incident["date_completed"]=stored_incident.date_completed.strftime("%d/%m/%Y, %H:%M:%S")
    incident["incident_date"]=stored_incident.incident_date.strftime("%d/%m/%Y, %H:%M:%S")
    if (stored_incident.upper_left_latlong != ""):
        incident["upper_left_latlong"]=stored_incident.upper_left_latlong
    if (stored_incident.lower_right_latlong != ""):
        incident["lower_right_latlong"]=stored_incident.lower_right_latlong
    if (include_sort_key): incident["srt_key"]=stored_incident.incident_date
    if (include_digraph):
        incident["digraph"]=str(generateIncidentDiGraph(stored_incident.uuid))
    if (include_manual_data_queuename):        
        incident["data_queue_name"]=incident_workflow.data_queue_name
    if (include_associated_data):
        incident["data_sets"]=[]
        for stored_ds in stored_incident.associated_datasets:
            incident["data_sets"].append(packageDataset(stored_ds))

        incident["data_sets"]=sorted(incident["data_sets"], key=itemgetter('date_created'), reverse=True)

    if (include_associated_data_transfers):
        incident["data_transfers"] = packageAllDataTransfersForDatasets(stored_incident.associated_datasets)

    return incident

@pny.db_session
def updateDataMetaData(data_uuid, incident_uuid, type, comments, username):
    incident = Incident[incident_uuid]
    user = User.get(username=username)
    if checkIfUserCanAccessIncident(incident, user):
        for stored_ds in incident.associated_datasets:
            if stored_ds.uuid==data_uuid:
                stored_ds.type=type
                stored_ds.comment=comments
                return True
    return False

@pny.db_session
def retrieveMatchingDatasets(data_type, incident_uuid, username):
    incident = Incident[incident_uuid]
    user = User.get(username=username)
    if checkIfUserCanAccessIncident(incident, user):
        returned_dataitems=[]
        for stored_ds in incident.associated_datasets:
            if stored_ds.type.lower() == data_type.lower():
                stored_ds_dict={}
                stored_ds_dict["uuid"]=stored_ds.uuid
                stored_ds_dict["name"]=stored_ds.name
                stored_ds_dict["type"]=stored_ds.type
                stored_ds_dict["comment"]=stored_ds.comment
                stored_ds_dict["date_created"]=stored_ds.date_created.strftime("%d/%m/%Y, %H:%M:%S")
                returned_dataitems.append(stored_ds_dict)
        return returned_dataitems
    return None

@pny.db_session
def retrieveDataMetaData(data_uuid, incident_uuid, username):
    incident = Incident[incident_uuid]
    user = User.get(username=username)
    if checkIfUserCanAccessIncident(incident, user):
        for stored_ds in incident.associated_datasets:
            if stored_ds.uuid==data_uuid: 
                stored_ds_dict={}
                stored_ds_dict["uuid"]=stored_ds.uuid
                stored_ds_dict["name"]=stored_ds.name
                stored_ds_dict["type"]=stored_ds.type
                stored_ds_dict["comment"]=stored_ds.comment
                stored_ds_dict["date_created"]=stored_ds.date_created.strftime("%d/%m/%Y, %H:%M:%S")
                return stored_ds_dict
    return None

@pny.db_session
def removeDataFromIncident(data_uuid, incident_uuid, username):
    incident = Incident[incident_uuid]
    user = User.get(username=username)
    if checkIfUserCanAccessIncident(incident, user):
        for stored_ds in incident.associated_datasets:
            if stored_ds.uuid==data_uuid: 
                stored_ds.delete()
                return True
    return False

@pny.db_session
def cancelIncident(incident_uuid, username):
    incident = Incident[incident_uuid]
    user = User.get(username=username)
    if checkIfUserCanAccessIncident(incident, user):
        workflow.OpenConnection()
        workflow.Cancel(incident_uuid)
        workflow.FlushMessages()
        workflow.CloseConnection()

@pny.db_session
def archiveIncident(incident_uuid, username):
    try:
        incident = Incident[incident_uuid]
        user = User.get(username=username)
        if checkIfUserCanAccessIncident(incident, user): 
            incident.status="ARCHIVED"
            return True
        else:
            return False
    except pny.core.ObjectNotFound as e:        
        return False

@pny.db_session
def activateIncident(incident_uuid, username):
    try:
        incident = Incident[incident_uuid]
        user = User.get(username=username)
        if checkIfUserCanAccessIncident(incident, user): 
            incident_workflow=RegisteredWorkflow.get(kind=incident.kind)
            if incident_workflow == None:
                print("Warning: 'incident_workflow' not defined")
                return False
            msg = {}
            msg["IncidentID"]=incident_uuid

            workflow.OpenConnection()
            workflow.send(message=msg, queue=incident_workflow.init_queue_name)
            workflow.FlushMessages()
            workflow.CloseConnection()
            return True
        else:
            print("Warning: User cannot access incident")
            return False
    except pny.core.ObjectNotFound as e:
        print("Warning: 'ObjectNotFound' error. Incident not found")
        print(e)
        return False

def doesStoredIncidentMatchFilter(stored_incident, pending_filter, active_filter, completed_filter, cancelled_filter, error_filter, archived_filter):
    if stored_incident.status=="PENDING":
        if pending_filter: return True        
        return False
    if stored_incident.status=="ACTIVE":
        if active_filter: return True        
        return False
    if stored_incident.status=="COMPLETE":
        if completed_filter: return True        
        return False
    if stored_incident.status=="CANCELLED":
        if cancelled_filter: return True        
        return False
    if stored_incident.status=="ERROR":
        if error_filter: return True        
        return False
    if stored_incident.status=="ARCHIVED":
        if archived_filter: return True        
        return False
    return False

@pny.db_session
def retrieveMyIncidentSummary(username, pending_filter, active_filter, completed_filter, cancelled_filter, error_filter, archived_filter):
    incidents=[]
    user = User.get(username=username)
    for stored_incident in user.incidents:
        if doesStoredIncidentMatchFilter(stored_incident, pending_filter, active_filter, completed_filter, cancelled_filter, error_filter, archived_filter):
            incidents.append(packageIncident(stored_incident, True, False, False, False, False, False))
    sorted_incidents=sorted(incidents, key = lambda i: (i['status'], i['srt_key']),reverse=True)
    for d in sorted_incidents:
        del d['srt_key']
    return sorted_incidents

@pny.db_session
def retrieveIncident(incident_uuid, username):    
    user = User.get(username=username)
    incident = Incident.get(uuid=incident_uuid)
    if checkIfUserCanAccessIncident(incident, user):
        return packageIncident(incident, False, True, True, True, True, True)
    return None
