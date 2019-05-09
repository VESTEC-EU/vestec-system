import logging
#import pika
from aio_pika.exchange import Message, ExchangeType
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

        connection - aio_pika.Connection - the AMQP server connection to use

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

    async def connect(self):
        """Connect to the server"""
        self.channel = await self.connection.channel()

        # Exchange for all machine proxy servers
        await self.channel.declare_exchange(name=self.exchange_name, type=ExchangeType.TOPIC)

        # Queue for this machine
        self.queue = await self.channel.declare_queue(self.queue_name)

        # Subscribe the queue to all messages for this machine
        await self.queue.bind(
            exchange=self.exchange_name,
            routing_key=self.routing_key,
        )
        log.info(
            'RpcServer "%s" has set up AMQP with exchange "%s", queue "%s" bound with key "%s"',
            self.name,
            self.exchange_name,
            self.queue_name,
            self.routing_key,
        )

    async def handle_message(self, msg):
        """API calls this when messages arrive

        Look up the name of the RPC method, deserialise arguments, get a
        connection manager, call the method, serialise the
        result, and send it back.
        """
        log.info("RPC call: %s", msg.routing_key)
        msg.ack()
        try:
            # Default is fail
            headers = {"success": "false"}
            assert msg.content_type == "application/json", (
                "Invalid content type '%s'" % msg.content_type
            )
            assert msg.content_encoding == "utf-8", (
                "Invalid encoding '%s'" % msg.content_encoding
            )
            # Which method?
            name, func_name = msg.routing_key.split(".")
            method_descr = getattr(self.API, func_name)
            # Get args
            args = method_descr.deserialise_args(msg.body)
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
            reply = Message(
                result_body,
                correlation_id=msg.correlation_id,
                content_type="application/json",
                content_encoding="utf-8",
                headers=headers,
            )
            await self.channel.default_exchange.publish(reply, msg.reply_to)

    async def start(self):
        """Start the server"""
        await self.connect()
        self.request_queue_consumer_tag = await self.queue.consume(self.handle_message)

    async def stop(self):
        """Stop the server"""
        # Stop consuming
        await self.queue.cancel(self.request_queue_consumer_tag)
        await self.channel.close()

    pass
