import pika
import functools
import sys
from db import db, MessageLog, Incident, initialise_database
import json
import pony.orm as pny
import uuid
import datetime
import time

import persist
from lock import atomic, _CleanLock

print(" [*] Opening connection to RabbitMQ server")
connection = pika.BlockingConnection(pika.ConnectionParameters(host="localhost"))
channel = connection.channel()

initialise_database()

# UUID for this running instance of the consumer (used for debugging when using multiple consumer processes)
ConsumerID = str(uuid.uuid4())

# stores messages that are to be sent
_sendqueue = []

# logger object exposed to handlers
Persist = persist._Persist()

# Creates an incident in the database. Returns the ncidentID
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

    print(" [*] Created incident %s" % id)

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
def Cancel(
    IncidentID,
    reason="",
    status="CANCELLED",
    CleanLocks=True,
    CleanPersist=True,
    CleanMessages=False,
    force=False,
):

    incident = Incident[IncidentID]
    incident.status = status
    incident.comment = reason

    print(" [*] Cancelled incident %s" % IncidentID)

    # send a cleanup message to the message queue
    _RequestCleanup(
        IncidentID,
        CleanLocks=CleanLocks,
        CleanPersist=CleanPersist,
        CleanMessages=CleanMessages,
        force=force,
    )


# Complete an Incident
@pny.db_session
def Complete(
    IncidentID, CleanLocks=True, CleanPersist=True, CleanMessages=False, force=False
):

    incident = Incident[IncidentID]
    incident.status = "COMPLETE"
    incident.date_completed = datetime.datetime.now()
    print(" [*] Completed incident %s" % IncidentID)

    # Send a cleanup message to the queue
    _RequestCleanup(
        IncidentID,
        CleanLocks=CleanLocks,
        CleanPersist=CleanPersist,
        CleanMessages=CleanMessages,
        force=force,
    )


# callback to register a handler with a queue, and also declare that queue to the RMQ system
def RegisterHandler(handler, queue):
    print(" [*] '%s' registered to queue '%s'" % (handler.__name__, queue))
    channel.queue_declare(queue=queue)
    channel.basic_consume(queue=queue, on_message_callback=handler, auto_ack=False)


# decorator to use for handlers. Handler function is to take one argument (the message)
def handler(f):
    @functools.wraps(f)
    def wrapper(ch, method, properties, body, **kwargs):
        global _sendqueue

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
                # This should only happen if a consumer process has died midway through processing
                # The re-process of the message should go ok but this warning will be printed
                if log.status != "SENT":
                    print(
                        " [*] ####### WARNING message is in processing state #########"
                    )
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
                # clear the send queue (throw away messages that were to be sent from the failed handler)
                _sendqueue = []
            else:
                # send the messages queued up by the handler
                FlushMessages()

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
# This does not actually send the message, but enqueues it to be sent
def send(message, queue):

    # Get the incident ID from the message
    try:
        incident = message["IncidentID"]
    except:
        raise Exception("Incident ID not included in the message")

    # check if the incident is still active. If not, don't send message
    if (not _IsActive(incident)) and queue != "_Cleanup":
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

    _sendqueue.append(
        {
            "queue": queue,
            "message": msg,
            "incident": incident,
            "caller": caller,
            "id": id,
        }
    )

    return


# Loops through enqueued messages and sends them
def FlushMessages():
    global _sendqueue
    for item in _sendqueue:
        msg = item["message"]
        queue = item["queue"]

        # check if the incident is still active. If not, don't send message
        incident = item["incident"]
        caller = item["caller"]
        id = item["id"]
        if (not _IsActive(incident)) and queue != "_Cleanup":
            print(" [#] Incident stopped. Aborting message send")
            return

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

    # clear the queue
    _sendqueue = []


# Requests to clean up the incident. This sends a message to the cleanup handler (see below)
def _RequestCleanup(
    IncidentID, CleanLocks=True, CleanPersist=True, CleanMessages=False, force=False
):
    message = {}
    message["IncidentID"] = IncidentID
    message["CleanLocks"] = CleanLocks
    message["CleanPersist"] = CleanPersist
    message["CleanMessages"] = CleanMessages
    message["Force"] = force

    # send message to instruct a cleanup of this incident
    send(message, "_Cleanup")


# Handler for a cleanup message to clean up a given incident.
@pny.db_session
def _Cleanup(ch, method, properties, body):
    msg = json.loads(body)
    IncidentID = msg["IncidentID"]

    print("")
    print(
        "--------------------------------------------------------------------------------"
    )

    messages = pny.select(
        m
        for m in MessageLog
        if (m.incident_id == IncidentID and m.status == "PROCESSING")
    )[:]

    if len(messages) > 0 and not msg["Force"]:
        # If some parts of the incident are still running we wait until they are finished
        # so we reject the message (send it back to the queue)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        print(" [*] Cannot clean up incident yet... messages still being processed")
        print(
            "--------------------------------------------------------------------------------"
        )
        print("")
        return

    # Log this message as being processed
    msgid = msg["MessageID"]
    log = MessageLog[msgid]
    log.date_received = datetime.datetime.now()
    log.status = "PROCESSING"
    log.consumer = ConsumerID

    print(" [*] Cleaning up Incident %s" % IncidentID)

    if msg["CleanLocks"]:
        _CleanLock(IncidentID)

    if msg["CleanPersist"]:
        Persist._Cleanup(IncidentID)

    print(" [*] Done!")

    print(
        "--------------------------------------------------------------------------------"
    )
    print("")

    log.date_completed = datetime.datetime.now()
    log.status = "COMPLETE"

    # finally acknowledge completion of message to rabbitmq
    ch.basic_ack(delivery_tag=method.delivery_tag)


# Closes a connection
def finalise():
    print(" [*] Closing connection to RabbitMQ server")
    print("")
    connection.close()


# Starts the workflow manager (starts waiting for messages to consume)
def execute():
    RegisterHandler(_Cleanup, "_Cleanup")
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
