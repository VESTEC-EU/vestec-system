import pony.orm as pny
import os
import datetime
import uuid

db = pny.Database()


class MessageLog(db.Entity):
    uuid = pny.PrimaryKey(str)
    status = pny.Required(str)
    date_submitted=pny.Required(datetime.datetime)
    date_received=pny.Optional(datetime.datetime)
    date_completed=pny.Optional(datetime.datetime)
    originator=pny.Required(str)
    destination = pny.Required(str)
    incident_id = pny.Required(str)
    message = pny.Required(str)
    comment = pny.Optional(str)
    consumer = pny.Optional(str)

class Incident(db.Entity):
    uuid = pny.PrimaryKey(str)
    kind = pny.Required(str)
    name = pny.Required(str)
    status = pny.Required(str,default="ACTIVE")
    comment = pny.Optional(str)

    date_started=pny.Required(datetime.datetime)
    date_completed=pny.Optional(datetime.datetime)

    incident_date=pny.Required(datetime.datetime)

    parameters = pny.Optional(str)



def initialise_database():
    dbpath="db.sqlite"

    db.bind("sqlite",dbpath,create_db=True)
    db.generate_mapping(create_tables=True)
    print("Database initialised")



if __name__ == "__main__":
    initialise_database()
    now = datetime.datetime.now()
    uuid = str(uuid.uuid4())
    uuidm = str(uuid.uuid4())
    with pny.db_session:
        Incident(uuid=uuid,kind="TEST",name="TESTING",date_started=now,incident_date=now)
        MessageLog(uuid=uuidm,status="SENT",date_submitted=now,originator="Testprog",destination="NONE",    incident_id=uuid,payload="TESTING TESTING")

    print("done?")