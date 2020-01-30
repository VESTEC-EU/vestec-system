import pika
import functools
import sys
from db import db, MessageLog, Incident, initialise_database
import json
import pony.orm as pny
import uuid
import datetime
import time

print(" [*] Opening connection to RabbitMQ server")
connection = pika.BlockingConnection(pika.ConnectionParameters(host="localhost"))
channel = connection.channel()

initialise_database()

# UUID for this running instance of the consumer (used for debugging when using multiple consumer processes)
ConsumerID = str(uuid.uuid4())


#### Code for a database to be used to store state information for the handlers

# Class that allows handlers to log some data
class _Logger:
    localDB = pny.Database()

    class DBlog(localDB.Entity):
        incident = pny.Required(str)
        originator = pny.Required(str)
        data = pny.Required(str)

    def __init__(self):
        self.localDB.bind(provider="sqlite", filename="handlers.sqlite", create_db=True)
        # self.localDB.bind(provider='sqlite', filename=":memory:") #cannot have an in-memory db if used between many processes
        self.localDB.generate_mapping(create_tables=True)

    # Called by handler... logs information to be persisted between calls
    def Log(self, incident, dict):
        originator = sys._getframe(1).f_code.co_name
        data = json.dumps(dict)
        with pny.db_session:
            self.DBlog(incident=incident, originator=originator, data=data)

    # called by handler - retrieives all the logs belonging to this incident and handler
    def GetLogs(self, incident):
        originator = sys._getframe(1).f_code.co_name
        with pny.db_session:
            logs = self.DBlog.select(
                lambda p: p.incident == incident and p.originator == originator
            )
            l = []
            for log in logs:
                dict = json.loads(log.data)
                l.append(dict)
        return l


# logger object exposed to handlers
Logger = _Logger()

###### END of state information database code


def CreateIncident(name, kind, incident_date=None):

    # get uuid for this event and set up some basic (dummy) parameters
    id = str(uuid.uuid4())
    date_started = datetime.datetime.now()
    if incident_date == None:
        incident_date = datetime.datetime.now()

    # create database entry
    with pny.db_session:
        Incident(
            uuid=id,
            kind=kind,
            name=name,
            date_started=date_started,
            incident_date=incident_date,
        )

    return id


# Test if a given Incident is active (returns True/False)
@pny.db_session
def _IsActive(IncidentID):
    try:
        return Incident[IncidentID].status == "ACTIVE"
    except:
        raise Exception("Unknown IncidentID")


# Cancel an Incident giving optional reasons and a named "status" (default CANCELLED)
@pny.db_session
def Cancel(IncidentID, reason="", status="CANCELLED"):
    incident = Incident[IncidentID]
    incident.status = status
    incident.comment = reason
    print(" [*] Cancelled incident %s" % IncidentID)


# Complete an Incident
@pny.db_session
def Complete(IncidentID):
    incident = Incident[IncidentID]
    incident.status = "COMPLETE"
    incident.date_completed = datetime.datetime.now()


# callback to register a handler with a queue, and also declare that queue to the RMQ system
def RegisterHandler(handler, queue):
    print(" [*] '%s' registered to queue '%s'" % (handler.__name__, queue))
    channel.queue_declare(queue=queue)
    channel.basic_consume(queue=queue, on_message_callback=handler, auto_ack=False)


# decorator to use for handlers. Handler function is to take one argument (the message)
def handler(f):
    @functools.wraps(f)
    def wrapper(ch, method, wrapper, body, **kwargs):

        print("")
        print(
            "--------------------------------------------------------------------------------"
        )
        print(" [*] Handler: %s" % f.__name__)

        # convert json message back to dictionary
        msg = json.loads(body)
        incident = msg["IncidentID"]
        mssgid = msg["MessageID"]

        print(" [*] Message: %s" % mssgid)
        print(" [*] Incident ID: %s" % incident)

        # Check if parent incident is active. If so, do some book keeping and execute handler
        try:
            active = _IsActive(incident)
        except:
            # we handle the lack of a valid IncidentID at the bottom of this function
            # so no need to dupicate code here
            active = False
            pass

        if active:
            # Log that we are processing the message
            with pny.db_session:
                log = MessageLog[mssgid]
                log.date_received = datetime.datetime.now()
                log.status = "PROCESSING"
                log.consumer = ConsumerID

            # call message handler
            print(" [*] Executing task")
            try:
                f(msg)
            except Exception as e:
                # If the handler throws an error, log this in the message log
                print(" [#] Error occurred: %s" % str(e))
                with pny.db_session:
                    log = MessageLog[mssgid]
                    log.status = "ERROR"
                    log.comment = "%s: %s" % (f.__name__, str(e))
                Cancel(
                    incident,
                    reason="%s error: %s" % (f.__name__, str(e)),
                    status="ERROR",
                )
            else:
                # log completion of task
                print(" [*] Task complete")
                with pny.db_session:
                    log = MessageLog[mssgid]
                    log.date_completed = datetime.datetime.now()
                    log.status = "COMPLETE"

        # Incident is not active (or not in database): log that we have not executed the handler
        else:
            # log non-completion of task
            with pny.db_session:

                log = MessageLog[mssgid]
                log.date_received = datetime.datetime.now()
                log.status = "NOT PROCESSED"
                try:
                    istatus = Incident[incident].status
                    log.comment = (
                        "Incident is no longer active with status %s" % istatus
                    )
                    print(" [*] Task not started: Incident stopped")
                except:
                    log.comment = "Incident ID not recognised"
                    print(" [*] Task not started: Incident ID not recognised")

        print(
            "--------------------------------------------------------------------------------"
        )
        print("")

        # finally acknowledge completion of message to rabbitmq
        ch.basic_ack(delivery_tag=method.delivery_tag)

    return wrapper


# routine to call when we want to send a message to a queue. Takes the message (in dict form) and the queue to send the message to as arguments
def send(message, queue):

    # Get the incident ID from the message
    try:
        incident = message["IncidentID"]
    except:
        raise Exception("Incident ID not included in the message")

    # check if the incident is still active. If not, don't send message
    if not _IsActive(incident):
        print(" [#] Incident stopped. Aborting message send")
        return

    # get name of caller function - this will be logger as the sender of the message
    caller = sys._getframe(1).f_code.co_name

    # create uuid for this message and add it to the message payload
    id = str(uuid.uuid4())
    message["MessageID"] = id
    message["originator"] = caller

    # convert the message to a json
    try:
        msg = json.dumps(message)
    except:
        raise Exception("Unable to jsonify message")

    # log the message
    with pny.db_session:
        MessageLog(
            uuid=id,
            status="SENT",
            date_submitted=datetime.datetime.now(),
            originator=caller,
            destination=queue,
            incident_id=incident,
            message=msg,
        )

    # send the message
    channel.basic_publish(exchange="", routing_key=queue, body=msg)

    # stuff to do after message is sent
    print(" [*] Sent message to queue '%s'" % (queue))


# Closes a connection
def finalise():
    print(" [*] Closing connection to RabbitMQ server")
    print("")
    connection.close()


#####A semaphore lock for if a handler needs to ensure it is the only version of it running at once

# database for the locks
lockDB = pny.Database()


class Lock(lockDB.Entity):
    name = pny.PrimaryKey(str)
    date = pny.Optional(datetime.datetime)
    locked = pny.Required(bool, default=False)


lockDB.bind(provider="sqlite", filename="locks.sqlite", create_db=True)
lockDB.generate_mapping(create_tables=True)

# check that an entry for this handler exists in the lock database
def _EnsureLockHandlerExists(name):
    with pny.db_session:
        if Lock.exists(name=name):
            return
        else:
            print(" [*] Creating LockDB entry for %s" % name)
            l = Lock(name=name)
            return


# This function gets a lock and returns once it has it
# Takes a name/label for the lock, and the incident this belongs to. Combines these to create a
# unique ID for the name
def GetLock(name, incident):
    if name == None or incident == None:
        raise Exception("Unable to lock: Lock requires a name and incident")
    else:
        name = name + incident

    # make sure there is an entry for this handler in the db
    _EnsureLockHandlerExists(name)

    # loop until we get a lock
    while True:
        with pny.db_session:
            l = Lock[name]
            if l.locked == False:
                l.locked = True
                l.date = datetime.datetime.now()
                print(" [*] Aquired Lock")
                return
            else:
                print(" [*] Lock not aquired. Will try again in 1 second")
        time.sleep(1)


# this function releases a lock
# Takes a name/label for the lock, and the incident this belongs to. Combines these to create a
# unique ID for the name
def ReleaseLock(name, incident):
    if name == None or incident == None:
        raise Exception("Lock requires a name and an incident")
    else:
        name = name + incident

    try:
        with pny.db_session:
            l = Lock[name]
            l.locked = False
            l.date = datetime.datetime.now()
            print(" [*] Lock released")
    except:
        raise Exception("Unable to unlock: unknown lock")


# a wrapper version of the above two functions for handlers so you can wrap a function/handler
def atomic(f):
    @functools.wraps(f)
    def wrapper(message, **kwargs):
        GetLock(f.__name__, message["IncidentID"])
        f(message)
        ReleaseLock(f.__name__, message["IncidentID"])

    return wrapper


######### END OF LOCK FUNCTIONALITY ###########################

# Starts the workflow manaeger (starts waiting for messages to consume)
def execute():
    print("")
    print(" [*] Workflow Manager ready to accept messages. To exit press CTRL+C \n")
    try:
        # Specify how many messages we want to prefetch... (may be important for load balancing)
        # channel.qos(prefetch_count=1)
        channel.start_consuming()
    except KeyboardInterrupt:
        print(" [*] Keyboard Interrupt detected")
    finally:
        print(" [*] Cleaning up")
        finalise()
        print("")
