import pika
import functools
import sys
from db import db, MessageLog, Incident, initialise_database
import json
import pony.orm as pny
import uuid
import datetime

print(" [*] Opening connection to RabbitMQ server")
connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()

initialise_database()


#### Code for a n in-memory database to be used to store local data

#Class that allows handlers to log some things to an in memory database
class _Logger():
    localDB = pny.Database()

    class DBlog(localDB.Entity):
            incident = pny.Required(str)
            originator = pny.Required(str)
            data = pny.Required(str)
    
    
    def __init__(self):
        #self.localDB.bind(provider='sqlite', filename='local.sqlite',create_db=True) #filename=":memory:"
        self.localDB.bind(provider='sqlite', filename=":memory:")
        self.localDB.generate_mapping(create_tables=True)
    
    #Called by handler... logs information to be persisted between calls
    def Log(self,incident,dict):
        originator = sys._getframe(1).f_code.co_name
        data = json.dumps(dict)
        with pny.db_session:
            self.DBlog(incident=incident,originator=originator,data=data)
    
    #called by handler - retrieives all the logs belonging to this incident and handler
    def GetLogs(self,incident):
        originator = sys._getframe(1).f_code.co_name
        with pny.db_session:
            logs = self.DBlog.select( lambda p: p.incident == incident and p.originator == originator)
            l = []
            for log in logs:
                dict = json.loads(log.data)
                l.append(dict)
        return l

#logger object exposed to handlers
Logger=_Logger()

#Test if a given Incident is active (returns True/False)
@pny.db_session
def _IsActive(IncidentID):
    return Incident[IncidentID].status == "ACTIVE"

#Cancel an Incident giving optional reasons and a named "status" (default CANCELLED)
@pny.db_session
def Cancel(IncidentID,reason="",status="CANCELLED"):
    incident=Incident[IncidentID]
    incident.status=status
    incident.comment=reason
    print(" [*] Cancelled incident %s"%IncidentID)

#Complete an Incident
@pny.db_session
def Complete(IncidentID):
    incident=Incident[IncidentID]
    incident.status="COMPLETE"
    incident.date_completed = datetime.datetime.now()


#callback to register a handler with a queue, and also declare that queue to the RMQ system
def RegisterHandler(handler, queue):
    print(" [*] '%s' registered to queue '%s'"%(handler.__name__,queue))
    channel.queue_declare(queue=queue)
    channel.basic_consume(queue=queue, on_message_callback=handler, auto_ack=True)

#decorator to use for handlers. Handler function is to take one argument (the message)
def handler(f):
    @functools.wraps(f)
    def wrapper(ch,method,wrapper,body,**kwargs):
        print("")
        print("--------------------------------------------------------------------------------")
        print(" [*] Handler: %s"%f.__name__)
        ######stuff to do before handler is called

         #convert json message back to dictionary
        msg = json.loads(body)
        incident = msg["IncidentID"]
        mssgid = msg["MessageID"]

        print(" [*] Message: %s"%mssgid)
        print(" [*] Incident ID: %s"%incident)
        
        #Check if parent incident is active. If so, do some book keeping and execute handler
        if _IsActive(incident):
            # Log receipt of message
            with pny.db_session:
                log = MessageLog[mssgid]
                log.date_received=datetime.datetime.now()
                log.status="PROCESSING"

            #call message handler
            print(" [*] Executing task")
            try:
                f(msg)
            except Exception as e:
                #If the handler throws an error, log this in the message log
                print(" [*] Error occurred: %s"%e.message)
                with pny.db_session:
                    log = MessageLog[mssgid]
                    log.status="ERROR"
                    log.comment=e.message
            else:            
            #######stuff to do after handler is successfully called
                #log completion of task
                print(" [*] Task complete")
                with pny.db_session:
                    log = MessageLog[mssgid]
                    log.date_completed=datetime.datetime.now()
                    log.status="COMPLETE"

        #Incident is not active: log that we have not executed the handler
        else:
            #log non-completion of task
            with pny.db_session:
                print(" [*] Task not started: Incident stopped")
                log = MessageLog[mssgid]
                log.date_received=datetime.datetime.now()
                log.status="NOT PROCESSED"
                istatus = Incident[incident].status
                log.comment="Incident is no longer active with status %s"%istatus

        print("--------------------------------------------------------------------------------")
        print("")

    
    return wrapper

#routine to call when we want to send a message to a queue. Takes the message (in dict form) and the queue to send the message to as arguments
def send(message,queue):
    ####stuff to do before message is sent

    # check if the incident is still active. If not, don't send message
    incident = message["IncidentID"]
    if not _IsActive(incident):
        print(" [*] Incident stopped. Aborting message send")
        return


    #get name of caller function
    caller = sys._getframe(1).f_code.co_name
    
    #create uuid for this message and add it to the message payload
    id = str(uuid.uuid4())
    message["MessageID"] = id
    message["originator"] = caller
    
    #convert the message to a json
    msg = json.dumps(message)

    #log the message
    with pny.db_session:
        MessageLog(uuid=id,status="SENT",date_submitted=datetime.datetime.now(),originator=caller,destination=queue,incident_id=incident,message=msg)
    
    #send the message
    channel.basic_publish(exchange='', routing_key=queue, body=msg)

    #stuff to do after message is sent
    print(" [*] Sent message to queue '%s'"%(queue))


# Closes a connection
def finalise():
    print(" [*] Closing connection to RabbitMQ server")
    print("")
    connection.close()


# Starts the workflow manaeger (starts waiting for messages to consume)
def execute(nprocs=1):
    print("")
    print(' [*] Workflow Manager ready to accept messages. To exit press CTRL+C \n')
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print(" [*] Keyboard Interrupt detected")
    finally:
        print(" [*] Cleaning up")
        finalise()
        print("")


