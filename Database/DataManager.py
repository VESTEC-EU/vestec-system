import pony.orm as pny
import uuid
import datetime
from Database import db


class Data(db.Entity):
    id = pny.PrimaryKey(str)
    machine = pny.Required(str)
    filename = pny.Required(str)
    type = pny.Required(str)
    path = pny.Optional(str)
    storage_technology = pny.Required(str,default="FILESYSTEM") #could be FILESYSTEM, VESTECDB, OBJECTSTORE
    description = pny.Required(str)
    size = pny.Required(int)
    metadata = pny.Optional(str) #json with optional "stuff" in it
    date_registered = pny.Required(datetime.datetime)
    date_modified = pny.Optional(datetime.datetime)
    status = pny.Required(str,default="ACTIVE") #could be ACTIVE, ARCHIVED, DELETED or UNKNOWN
    originator = pny.Required(str) #where the data came from, e.g. a website, simulation output, some user
    group = pny.Required(str) #what the data belongs to, e.g. fire, space weather etc
    modifylock = pny.Required(int,default=0) #a lock for if something is being modified (e.g. if we are in the process of moving an object, we don't want to be able to copy it at the same time)
    data_transfers_src = pny.Set("DataTransfer") # data transfers, where these data are the source
    data_transfers_dst = pny.Set("DataTransfer") # data transfers, where these data are the destination

# table for non-blocking tasks
class Tasks(db.Entity):
    id = pny.PrimaryKey(str)
    status = pny.Required(str,default="QUEUED") #options are QUEUED, RUNNING, COMPLETE, ERROR(, CANCELLED?)
    metadata = pny.Required(str) #The info required to carry out the operation
    tasktype = pny.Required(str) #the type of operation (COPY, MOVE, DOWNLOAD etc...)
    t_submit = pny.Required(datetime.datetime) #time this taks was submitted
    t_start = pny.Optional(datetime.datetime) #time this task was started
    t_end = pny.Optional(datetime.datetime) #time this task was finished
    result = pny.Optional(str) # a message from the handler. This could be an error message, or the UUID of the completed file object

class DataTransfer(db.Entity):
    """ Database entity for data transfers """
    id = pny.PrimaryKey(str)
    src = pny.Required(Data, reverse="data_transfers_src") # allows to get durther information about data
    dst = pny.Optional(Data, reverse="data_transfers_dst") # might be different from src if file is copied
    src_machine = pny.Required(str)
    dst_machine = pny.Required(str)
    #date_submitted = pny.Required(datetime.datetime) # might be necessary for non-blocking data transfer
    date_started = pny.Required(datetime.datetime)
    date_completed = pny.Optional(datetime.datetime)
    completion_time = pny.Optional(datetime.timedelta)
    status = pny.Required(str)

