import workflow
import uuid
from db import Incident
import pony.orm as pny
import datetime
import time


def submit_fire(id):
    
    #create a basic message dictionary
    msg = {}
    msg["IncidentID"]=id
    msg["data"] = "blah blah blah"



    #send the messages to relevant queues to kick off the workflow
    workflow.send(message=msg,queue="fire_terrain")
    workflow.send(message=msg,queue="fire_hotspot")
    workflow.send(message=msg,queue="weather_data")


def create_fire_incident():

    #get uuid for this event and set up some basic (dummy) parameters
    id = str(uuid.uuid4())
    name = "Test fire"
    kind="FIRE"
    date_started=datetime.datetime.now()
    incident_date=datetime.datetime.now()
    
    #create database entry
    with pny.db_session:
        Incident(uuid=id,kind=kind,name=name,date_started=date_started,incident_date=incident_date)

    submit_fire(id)

    # time.sleep(1.5)
    # workflow.Cancel(id,reason="Test cancellation")






if __name__ == "__main__":
    create_fire_incident()
    workflow.finalise()
