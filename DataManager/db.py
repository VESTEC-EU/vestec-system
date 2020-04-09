import pony.orm as pny
import uuid
import datetime

db = pny.Database()

class Data(db.Entity):
    id = pny.PrimaryKey(str)
    machine = pny.Required(str)
    filename = pny.Required(str)
    path = pny.Required(str)
    description = pny.Required(str)
    size = pny.Required(int)
    metadata = pny.Optional(str) #json with optional "stuff" in it
    date_registered = pny.Required(datetime.datetime)
    date_modified = pny.Optional(datetime.datetime)
    status = pny.Required(str,default="ACTIVE") #could be ACTIVE, ARCHIVED, DELETED or UNKNOWN
    originator = pny.Required(str) #where the data came from, e.g. a website, simulation output, some user
    group = pny.Required(str) #what the data belongs to, e.g. fire, space weather etc


def initialise_database():
    db.bind("sqlite", "db.sqlite", create_db=True)
    db.generate_mapping(create_tables=True)