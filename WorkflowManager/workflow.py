import pika
import functools
import sys

print(" [*] Opening connection to RabbitMQ server")
connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()

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
        #stuff to do before handler is called
        f(body)
        #stuff to do after handler is called
        print("--------------------------------------------------------------------------------")
        print("")

    
    return wrapper

#routine to call when we want to send a message to a queue. Takes the message and the queue to send the message to as arguments
def send(message,queue):
    #stuff to do before message is sent
    channel.basic_publish(exchange='', routing_key=queue, body=message)
    #stuff to do after message is sent
    print(" [*] Sent message '%s' to queue '%s'"%(message,queue))


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


