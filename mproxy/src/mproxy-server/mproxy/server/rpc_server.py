import logging
import pika

log = logging.getLogger(__name__)


class RpcServer:
    from mproxy.core import API

    def __init__(
        self,
        name,
        factory,
        connection,
        exchange_name="machine_proxy",
        queue_name=None,
        routing_key=None,
    ):
        """Create an RPC server that listens on the AMQP `connection` and
        forwards method calls to an object
        
        name - str - Identifier of the machine that we are proxying
        
        factory - callable - Factory function for making connection manager objects for the named machine

        connection - pika.Connection - the AMQP server connection to use

        exchange_name - str - Exchange to declare on server (default == 'machine_proxy')

        queue_name - str - Queue to declare on server (default == name)

        routing_key - str - Topic key to subscribe to (default == name.*)
        """

        self.name = name
        self.factory = factory
        self.connection = connection

        # Process defaults
        self.queue_name = name if queue_name is None else queue_name
        self.exchange_name = exchange_name
        self.routing_key = "{}.*".format(name) if routing_key is None else routing_key

        self.channel = connection.channel()

        # Exchange for all machine proxy servers
        self.channel.exchange_declare(exchange=self.exhange_name, exchange_type="topic")

        # Queue for this machine
        self.channel.queue_declare(self.queue_name)

        # Subscribe the queue to all messages for this machine
        self.channel.queue_bind(
            exchange=self.exchange_name,
            queue=self.queue_name,
            routing_key=self.routing_key,
        )
        log.info(
            'RpcServer "%s" has set up AMQP with exchange "%s", queue "%s" bound with key "%s"',
            name,
            self.exchange_name,
            self.queue_name,
            self.routing_key,
        )

    def handle_message(self, channel, method, props, body):
        """Pika API calls this when messages arrive

        Look up the name of the RPC method, deserialise arguments, get a
        connection manager, call the method, serialise the
        result, and send it back.
        """
        log.info("RPC call: %s", method.routing_key)
        channel.basic_ack(delivery_tag=method.delivery_tag)
        try:
            # Default is fail
            headers = {"success": "false"}
            assert props.content_type == "application/json", (
                "Invalid content type '%s'" % props.content_type
            )
            assert props.content_encoding == "utf-8", (
                "Invalid encoding '%s'" % props.content_encoding
            )
            # Which method?
            name, func_name = method.routing_key.split(".")
            method_descr = getattr(self.API, func_name)
            # Get args
            args = method_descr.deserialise_args(body)
            # Create/get the object that actually does the work
            conn_mgr = self.factory(self.name)
            # Run the method
            result = method_descr.call_with(conn_mgr, args)
            # Pack result
            result_body = method_descr.serialise_result(result)
            # We are OK if we got here
            headers = {"success": "true"}
        except Exception as e:
            result_body = b'"An error occurred"'
            log.exception("Exception while handling RPC call")
        finally:
            # Post the RPC reply message
            channel.basic_publish(
                exchange="",
                routing_key=props.reply_to,
                properties=pika.BasicProperties(
                    correlation_id=props.correlation_id,
                    content_type="application/json",
                    content_encoding="utf-8",
                    headers=headers,
                ),
                body=result_body,
            )

    def start(self):
        """Run the server - this runs forever"""
        self.channel.basic_consume(
            queue=self.queue_name, on_message_callback=self.handle_message
        )
        self.channel.start_consuming()

    pass
