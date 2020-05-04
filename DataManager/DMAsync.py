import sys
sys.path.append("../")
import pika
import os
import json
import time
import pony.orm as pny
import uuid
import datetime
from Database import db, initialiseDatabase, Data, DataTransfer, DMTasks
from operations import _checkExists, _copy, _register, _download


async_queue = "DM_Async"

OK=0
FILE_ERROR=1
NOT_IMPLEMENTED = 2

#opens a connection to the RMQ server
def OpenConnection():
    i=0
    while(True):
        i+=1
        # Try to open a connection to the rmq server
        if "VESTEC_RMQ_SERVER" in os.environ:
            host = os.environ["VESTEC_RMQ_SERVER"]
            print("Attempting to connect to RabbitMQ server `%s`"%host)
        else:
            print("Environment variable VESTEC_RMQ_SERVER not set. Defaulting to `localhost`")
            host="localhost"
        try:
            print(" [*] Opening connection to RabbitMQ server")
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
        except pika.exceptions.AMQPConnectionError as e:
            if i<5:
                print("Cannot connect to RabbitMQ server. Will try again in 5 seconds...")
                time.sleep(5)
            else:
                print("Cannot create connection to AMQP server... Maybe it's down?")
                raise Exception("Cannot create connection to AMQP server... Maybe it's down?")
        else:
            break

    channel = connection.channel()
    return connection, channel
    

# Closes a connection
def CloseConnection(connection):
    print(" [*] Closing connection to RabbitMQ server")
    connection.close()


@pny.db_session
def SubmitTask(message):
    #get an ID for the task
    id = str(uuid.uuid4())

    message["id"]=id
    
    #convert the message to json to be sent over rmq
    msg = json.dumps(message)
    
    #create database entry for the task
    task = DMTasks(id=id, metadata=msg,tasktype=message["operation"],t_submit=datetime.datetime.now())

    #commit this to the database 
    # makes sure it is in the database before the task is submitted 
    # meaning the task definitely has a db entry to look up
    pny.commit()
 
    try:
        #open connection, send message, close connection
        connection, channel = OpenConnection()
        channel.basic_publish(exchange="", routing_key=async_queue, body=msg)
        CloseConnection(connection)
    except Exception as e:
        print("Error sending message: %s"%str(e))
        task.status = "ERROR"
        task.result="Error sending message: %s"%str(e)
        pny.commit()
        raise e

    return id


def ExecuteTask(ch, method, properties, body):
    #the handler that executes the task
    try:
        msg = json.loads(body.decode('ascii'))
        
        id = msg["id"]
        with pny.db_session:
            task = DMTasks[id]
            task.t_start = datetime.datetime.now()

            tasktype = task.tasktype
            task.status = "RUNNING"
        
        print("##############################################")
        print("Hello from callback!")
        print("Task type = %s"%tasktype)
        print("message = '%s'"%msg)

        if tasktype == "MOVE" or tasktype == "COPY":

            src = msg["src"]
            src_machine = msg["src_machine"]
            dest = msg["dest"]
            dest_machine = msg["dest_machine"]
            fileID = msg["fileID"]
            description = msg["description"]
            size = msg["size"]
            originator = msg["originator"]
            group = msg["group"]

            path, fname = os.path.split(dest)

        elif tasktype == "DOWNLOAD":
            fname = msg["fname"]
            path = msg["path"] 
            machine= msg["machine"]
            url = msg["url"]
            protocol = msg["protocol"]
            options = msg["options"]
            description = msg["description"]
            originator = msg["originator"]
            group = msg["group"]

    

        else:
            with pny.db_session:
                task = DMTasks[id]
                task.result="Unknown task type %s"%tasktype
                task.status = 'ERROR'
                task.exit_code = NOT_IMPLEMENTED
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        

        print("Processing...")

        if tasktype == "COPY":
            status, message = _copy(src=src,src_machine=src_machine,dest=dest, dest_machine=dest_machine, id=fileID)
            if status == OK:
                message = _register(fname,path,dest_machine,description,size,originator,group)

        elif tasktype == "MOVE":
            status, message = _copy(src=src,src_machine=src_machine,dest=dest, dest_machine=dest_machine,id=fileID,move=True)
            if status == OK:
                with pny.db_session:
                    d=Data[fileID]
                    d.machine = dest_machine
                    path,fname = os.path.split(dest)
                    d.filename = fname
                    d.path = path
        elif tasktype == "DOWNLOAD":
            status, message = _download(fname,path,machine,url,protocol,options)
            if status == OK:
                size=options["size"]
                message=_register(fname,path,machine,description,size,originator,group)
                
        else:
            status=NOT_IMPLEMENTED
            message="Opertion %s unknown or not implemented"%tasktype

        print(status, message)

        with pny.db_session:
            task = DMTasks[id]
            task.t_end = datetime.datetime.now()
            task.result=message
            if status == OK:
                task.status = "COMPLETE"
            else:
                task.status = 'ERROR'

            task.exit_code = status
            

        print("##############################################")
        

    except Exception as e:
        ch.basic_ack(delivery_tag=method.delivery_tag)
        raise e



    ch.basic_ack(delivery_tag=method.delivery_tag)
    return None



def RegisterHandler(channel,handler, queue):
    print("'%s' registered to queue '%s'" % (handler.__name__, queue))
    channel.queue_declare(queue=queue)
    channel.basic_consume(queue=queue, on_message_callback=handler, auto_ack=False)



if __name__ == "__main__":
    try:
        initialiseDatabase()
        connection, channel = OpenConnection()
        RegisterHandler(channel,ExecuteTask,async_queue)
        # Specify how many messages we want to prefetch... (may be important for load balancing)
        channel.basic_qos(prefetch_count=10)
        print(" [*] Ready to comsume messages")
        channel.start_consuming()
    except KeyboardInterrupt:
        print(" [*] Keyboard Interrupt detected")
        print(" [*] Cleaning up")
        CloseConnection(connection)
    except pika.exceptions.ConnectionClosedByBroker as e:
        print(" [#] RabbitMQ server has shut down. Connection lost")
        print(e)
        
    except Exception as e:
        print(" [#] Unknown error has occurred. Shutting down the workflow engine")
        CloseConnection(connection)
        raise e
