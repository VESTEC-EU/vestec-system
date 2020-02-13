import pika
import functools
import sys
from db import db, MessageLog, Incident, initialise_database
import json
import pony.orm as pny
import uuid
import datetime
import time

import utils
import persist
from lock import atomic, _CleanLock

logger = utils.GetLogger(__name__)

# allows a user to set the logging level of the loggers
def SetLoggingLevel(level):
    utils.SetLevel(level)


print(" [*] Opening connection to RabbitMQ server")

# Try to open a connection to the rmq server
try:
    connection = pika.BlockingConnection(pika.ConnectionParameters(host="localhost"))
except pika.exceptions.AMQPConnectionError as e:
    logger.critical("Cannot create connection to AMQP server... Maybe it's down?")
    raise e

channel = connection.channel()

# initialise (connect to) the workflow database
initialise_database()

# UUID for this running instance of the consumer (used for debugging when using multiple consumer processes)
ConsumerID = str(uuid.uuid4())

# stores messages that are to be sent
_sendqueue = []

# object exposed to handlers to let them persist data
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

    logger.info("Created incident %s" % id)

    return id


# Test if a given Incident is active (returns True/False)
@pny.db_session
def _IsActive(IncidentID):
    try:
        return Incident[IncidentID].status == "ACTIVE"
    except pny.core.ObjectNotFound as e:
        logger.error("_IsActive: Unknown IncidentID %s" % (IncidentID))
        raise Exception("_IsActive: Unknown IncidentID %s" % (IncidentID)) from None


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
    try:
        incident = Incident[IncidentID]
    except pny.core.ObjectNotFound as e:
        logger.error("workflow.cancel: Unknown IncidentID %s" % IncidentID)
        raise Exception("workflow.cancel: Unknown IncidentID %s" % IncidentID) from None
    if incident.status != "ACTIVE":
        # incident is already not active, don't need to do anything here besides print message
        logger.warning(
            "Tried to cancel %s but it is inactive with status %s"
            % (IncidentID, incident.status)
        )
        return
    incident.status = status
    incident.comment = reason

    logger.info("Cancelled incident %s" % IncidentID)

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
    try:
        incident = Incident[IncidentID]
    except pny.core.ObjectNotFound as e:
        logger.error("workflow.Complete: Unknown IncidentID %s" % IncidentID)
        raise Exception(
            "workflow.Complete: Unknown IncidentID %s" % IncidentID
        ) from None

    if incident.status != "ACTIVE":
        # incident is already not active, don't need to do anything here besides print message
        logger.warn(
            "Tried to complete %s but it is inactive with status %s"
            % (IncidentID, incident.status)
        )
        return

    incident.status = "COMPLETE"
    incident.date_completed = datetime.datetime.now()

    logger.info("Completed incident %s" % IncidentID)

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
    logger.info("'%s' registered to queue '%s'" % (handler.__name__, queue))
    channel.queue_declare(queue=queue)
    channel.basic_consume(queue=queue, on_message_callback=handler, auto_ack=False)


# decorator to use for handlers. Handler function is to take one argument (the message)
def handler(f):
    @functools.wraps(f)
    def wrapper(ch, method, properties, body, **kwargs):

        # convert json message back to dictionary

        msg = json.loads(body)

        incident = msg["IncidentID"]
        mssgid = msg["MessageID"]

        logger.debug(
            "Recieved message %s for incident %s. Handler is %s"
            % (mssgid, incident, f.__name__)
        )

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
                    logger.warn(
                        "Message %s seems to have been handled previously" % mssgid
                    )
                log.date_received = datetime.datetime.now()
                log.status = "PROCESSING"
                log.consumer = ConsumerID

            # call message handler
            logger.info("Executing handler %s for indicent %s" % (f.__name__, incident))
            try:
                f(msg)
            except Exception as e:
                # If the handler throws an unknown error, log this in the message log
                logger.error(
                    "Exception occurred when executing %s" % f.__name__, exc_info=True
                )
                with pny.db_session:
                    log = MessageLog[mssgid]
                    log.status = "ERROR"
                    log.comment = "%s: %s" % (f.__name__, str(e))

                # clear the send queue (throw away messages that were to be sent from the failed handler)
                _sendqueue.clear()

                # Cancel this incident as we do not know what to do from here if a handler fails
                Cancel(
                    incident,
                    reason="%s error: %s" % (f.__name__, str(e)),
                    status="ERROR",
                )

                # make sure we send the cleanup message
                FlushMessages()

            else:
                # log completion of task
                logger.info(
                    "Handler %s for indicent %s completed successfully"
                    % (f.__name__, incident)
                )
                with pny.db_session:
                    log = MessageLog[mssgid]
                    log.date_completed = datetime.datetime.now()
                    log.status = "COMPLETE"

                # send the messages queued up by the handler
                FlushMessages()

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
                    logger.info(
                        "Handler %s for indicent %s not started: incident is no longer active"
                        % (f.__name__, incident)
                    )
                except pny.core.ObjectNotFound as e:
                    log.comment = "Incident ID not recognised"
                    logger.error(
                        "Incident ID %s not recognised. Cannot start handler"
                        % incident,
                        exc_info=True,
                    )

        # finally acknowledge completion of message to rabbitmq
        ch.basic_ack(delivery_tag=method.delivery_tag)

    return wrapper


# routine to call when we want to send a message to a queue. Takes the message (in dict form) and the queue to send the message to as arguments
# This does not actually send the message, but enqueues it to be sent
def send(message, queue):

    # Get the incident ID from the message
    try:
        incident = message["IncidentID"]
    except KeyError:
        logger.error("workflow.send: Incident ID not included in the message")
        raise Exception(
            "workflow.send: Incident ID not included in the message"
        ) from None

    # check if the incident is still active. If not, don't send message
    if (not _IsActive(incident)) and queue != "_Cleanup":
        logger.warn(
            "Message not queued for sending as incident %s is no longer active"
            % incident
        )
        return

    # get name of caller function - this will be logged as the sender of the message
    caller = sys._getframe(1).f_code.co_name

    # create uuid for this message and add it to the message payload
    id = str(uuid.uuid4())
    message["MessageID"] = id
    message["originator"] = caller

    # convert the message to a json
    try:
        msg = json.dumps(message)
    except ValueError as e:
        logger.error("workflow.send: Unable to jsonify message")
        raise Exception("workflow.send: Unable to jsonify message") from None

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

    # loop over all messages in the send queue
    while _sendqueue:

        message = _sendqueue.pop()

        msg = message["message"]
        queue = message["queue"]
        incident = message["incident"]
        caller = message["caller"]
        id = message["id"]

        # check if the incident is still active. If not, don't send message
        if (not _IsActive(incident)) and queue != "_Cleanup":
            logger.warn(
                "Message(s) not sent as incident %s is no longer active" % incident
            )
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
        logger.info("Sent message id %s to queue %s" % (id, queue))


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
    # THIS WILL ONLY BE SENT IF _RequestCleanup is called within a handler else we need to FlushMessages()
    send(message, "_Cleanup")


# Handler for a cleanup message to clean up a given incident.
@pny.db_session
def _Cleanup(ch, method, properties, body):
    msg = json.loads(body)
    IncidentID = msg["IncidentID"]

    messages = pny.select(
        m
        for m in MessageLog
        if (m.incident_id == IncidentID and m.status == "PROCESSING")
    )[:]

    if len(messages) > 0 and not msg["Force"]:
        # If some parts of the incident are still running we wait until they are finished
        # so we reject the message (send it back to the queue)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

        logger.debug(
            "Cannot clean up incident %s yet... Messages are still being processed. Requeueing"
            % IncidentID
        )
        return

    # Log this message as being processed
    msgid = msg["MessageID"]
    log = MessageLog[msgid]
    log.date_received = datetime.datetime.now()
    log.status = "PROCESSING"
    log.consumer = ConsumerID

    logger.info("Cleaning up Incident %s" % IncidentID)

    if msg["CleanLocks"]:
        _CleanLock(IncidentID)

    if msg["CleanPersist"]:
        Persist._Cleanup(IncidentID)

    logger.info("Clean up of incident %s complete!" % IncidentID)

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
        print(" [*] Cleaning up")
        finalise()
    except pika.exceptions.ConnectionClosedByBroker as e:
        logger.critical("RabbitMQ server has shut down. Connection lost", exc_info=True)
        print(" [#] RabbitMQ server has shut down. Connection lost")

    except Exception as e:
        print(" [#] Unknown error has occurred. Shutting down the workflow engine")
        logger.critical(
            "Unknown error occurred. Shutting down the workflow engine.", exc_info=True
        )
        finalise()
