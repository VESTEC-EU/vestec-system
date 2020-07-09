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
    upper_left_latlong = pny.Optional(str)
    lower_right_latlong = pny.Optional(str)
    duration = pny.Optional(int)

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
    date_created = pny.Required(datetime.datetime)
    status = pny.Required(str,default="PENDING")
    status_updated = pny.Required(datetime.datetime)
    directory = pny.Required(str)
    status_message = pny.Optional(str)
    machine = pny.Optional("Machine")
    queue = pny.Optional(str)
    jobID = pny.Optional(str)
    wkdir = pny.Optional(str)
    executable = pny.Required(str)
    kind = pny.Required(str)
    results_handler = pny.Optional(str)
    requested_walltime = pny.Optional(str)
    walltime = pny.Optional(str)
    num_nodes = pny.Optional(int)
    queue_state_calls = pny.Set("SimulationStateWorkflowCalls")
    performance_data = pny.Set("PerformanceData")
    
class SimulationStateWorkflowCalls(db.Entity):
    id = pny.PrimaryKey(int, auto=True)
    queue_state = pny.Required(str)
    call_name = pny.Required(str)
    simulation = pny.Required(Simulation)

#lock for workflow handlers
class Lock(db.Entity):
    name = pny.PrimaryKey(str)
    date = pny.Optional(datetime.datetime)
    locked = pny.Required(bool, default=False)

#a log for the handlers to persist some data
class HandlerLog(db.Entity):
    incident = pny.Required(str)
    originator = pny.Required(str)
    data = pny.Required(pny.LongStr)

class RegisteredWorkflow(db.Entity):
    kind=pny.Required(str)
    init_queue_name=pny.Required(str)
    data_queue_name=pny.Optional(str)
    test_workflow = pny.Required(bool, default=False, sql_default='0')
    users = pny.Set("User")
