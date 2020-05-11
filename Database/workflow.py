import pony.orm as pny
from Database import db
from Database.users import User
import datetime
import uuid

#these are all db tables related to the workflow system

class MessageLog(db.Entity):
    uuid = pny.PrimaryKey(str)
    status = pny.Required(str)
    date_submitted = pny.Required(datetime.datetime)
    date_received = pny.Optional(datetime.datetime)
    date_completed = pny.Optional(datetime.datetime)
    completion_time = pny.Optional(datetime.timedelta)
    originator = pny.Required(str)
    destination = pny.Required(str)
    incident_id = pny.Required(str)
    message = pny.Required(str)
    comment = pny.Optional(str)
    consumer = pny.Optional(str)
    src_tag = pny.Optional(str) #optional name for the sender (for workflow graph visualisation)
    dest_tag = pny.Optional(str) #optional name for the reciever (for workflow graph visualisation)

class StoredDataset(db.Entity):
    uuid = pny.PrimaryKey(str)
    name = pny.Optional(str)
    type = pny.Optional(str)
    comment = pny.Optional(str)
    incident = pny.Required("Incident")
    date_created = pny.Optional(datetime.datetime)

class Incident(db.Entity):
    uuid = pny.PrimaryKey(str)
    kind = pny.Required(str)
    name = pny.Required(str)
    status = pny.Required(str, default="PENDING")
    comment = pny.Optional(str)
    user_id = pny.Optional(User)
    upper_right_latlong = pny.Optional(str)
    lower_left_latlong = pny.Optional(str)

    date_started = pny.Required(datetime.datetime)
    date_completed = pny.Optional(datetime.datetime)

    incident_date = pny.Required(datetime.datetime)

    parameters = pny.Optional(str)

    simulations = pny.Set("Simulation")

    associated_datasets = pny.Set(StoredDataset)

#Stores records of simulations submitted to HPC machines
class Simulation(db.Entity):
    uuid = pny.PrimaryKey(str)
    incident = pny.Required(Incident)
    status = pny.Required(str,default="NOT SUBMITTED")
    machine = pny.Optional(str)
    queue = pny.Optional(str)
    jobID = pny.Optional(str)
    wkdir = pny.Optional(str)
    results_handler = pny.Optional(str)
    walltime = pny.Optional(datetime.timedelta)
    nodes = pny.Optional(int)


#lock for workflow handlers
class Lock(db.Entity):
    name = pny.PrimaryKey(str)
    date = pny.Optional(datetime.datetime)
    locked = pny.Required(bool, default=False)

#a log for the handlers to persist some data
class HandlerLog(db.Entity):
    incident = pny.Required(str)
    originator = pny.Required(str)
    data = pny.Required(str)

class RegisteredWorkflow(db.Entity):
	kind=pny.Required(str)
	init_queue_name=pny.Required(str)
	data_queue_name=pny.Optional(str)
	users = pny.Set("User")
