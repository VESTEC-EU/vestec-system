from WorkflowManager import workflow
from Database.users import User
from Database.workflow import Incident
import pony.orm as pny
from flask import jsonify
from flask_jwt_extended import get_jwt_identity
from functools import wraps
import datetime

@pny.db_session
def createIncident(incident_name, incident_kind, username):
    user_id = User.get(username=username)
    job_id = workflow.CreateIncident(incident_name, incident_kind, user_id=user_id)

    return job_id

def packageIncident(stored_incident):
    incident={}
    incident["uuid"]=stored_incident.uuid
    incident["kind"]=stored_incident.kind
    incident["name"]=stored_incident.name
    incident["status"]=stored_incident.status
    incident["comment"]=stored_incident.comment         
    incident["creator"]=stored_incident.user_id.username
    incident["date_started"]=stored_incident.date_started.strftime("%d/%m/%Y, %H:%M:%S")    
    if (stored_incident.date_completed is not None):
        incident["date_completed"]=stored_incident.date_completed.strftime("%d/%m/%Y, %H:%M:%S")
    incident["incident_date"]=stored_incident.incident_date.strftime("%d/%m/%Y, %H:%M:%S")
    return incident

@pny.db_session
def retrieveMyIncidents(username):
    incidents=[]
    user = User.get(username=username)
    for stored_incident in user.incidents:        
        incidents.append(packageIncident(stored_incident))
    return incidents

@pny.db_session
def retrieveIncident(incident_uuid, username):    
    user = User.get(username=username)
    incident = Incident.get(uuid=incident_uuid)
    if (incident is not None and user is not None):
        if (incident.user_id.user_id==user.user_id):
            return packageIncident(incident)    
    return None
