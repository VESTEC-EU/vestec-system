import uuid
from aio_pika import Message, ExchangeType
from aio_pika.tools import shield

from mproxy.core.api import API


def proxy(meth_descr):
    """Synthesise a method from the RPC method description.
    
    Requires that the class they are added to has a method `_rpc_call`
    which actually sends and gets raw bytes we can deal with.
    """

    async def call(self, *args, **kwargs):
        payload = meth_descr.serialise_args(*args, **kwargs)
        response = await self._rpc_call(meth_descr.name, payload)
        return meth_descr.deserialise_result(response)

    call.__doc__ = meth_descr.doc
    call.__name__ = meth_descr.name
    return call


class Client:
    """Forward API methods to the RPC server
    """

    # TODO: It would be nice to have these all method descriptors done
    # by a class decorator
    run = proxy(API.run)
    put = proxy(API.put)
    get = proxy(API.get)
    cd = proxy(API.cd)
    getcwd = proxy(API.getcwd)
    ls = proxy(API.ls)
    mkdir = proxy(API.mkdir)
    rm = proxy(API.rm)
    rmdir = proxy(API.rmdir)
    mv = proxy(API.mv)

    @classmethod
    async def create(cls, name, connection, exchange_name="machine_proxy"):
        ans = cls(name, connection, exchange_name)
        await ans.connect()
        return ans

    def __init__(self, name, connection, exchange_name="machine_proxy"):

        self.name = name
        self.connection = connection
        self.exchange_name = exchange_name
        self._req_responses = {}

    @shield
    async def connect(self):
        self.channel = await self.connection.channel()
        # Declare exchange we're submitting RPCs to
        self.exchange = await self.channel.declare_exchange(
            name=self.exchange_name, type=ExchangeType.TOPIC
        )
        # Declare my response queue
        self.response_q = await self.channel.declare_queue("", exclusive=True)
        self.response_q_consumer_tag = await self.response_q.consume(
            self._handle_response
        )
        self.channel.add_close_callback(self._on_close)

    def _on_close(self, exc=None):
        log.debug("Closing RPC futures because %r", exc)
        for future in self._req_responses.values():
            if not future.done():
                future.set_exception(exc or Exception)

    async def disconnect(self):
        await self.response_q.cancel(self.response_q_consumer_tag)
        # response Q will be auto-deleted since it's exclusive

    def _handle_response(self, msg):
        corr_id = msg.correlation_id
        future = self._req_responses.pop(corr_id, None)

        assert future is not None, "No outstanding request with ID: %s" % corr_id
        try:
            assert msg.content_type == "application/json"
            assert msg.content_encoding == "utf-8"
        except AssertionError as e:
            future.set_exception(e)
            return

        headers = msg.headers
        ok = {"true": True, "false": False}[headers["success"]]
        if ok:
            future.set_result(msg.body)
        else:
            future.set_exception(ValueError(msg.body))

    async def _rpc_call(self, method_name, payload):
        topic = "{}.{}".format(self.name, method_name)
        corr_id = str(uuid.uuid4())
        future = self.connection.loop.create_future()

        self._req_responses[corr_id] = future
        msg = Message(
            payload,
            reply_to=self.response_q,
            correlation_id=corr_id,
            content_type="application/json",
            content_encoding="utf-8",
        )
        await self.exchange.publish(msg, routing_key=topic)
        # Return the response when it arrives
        return await future
