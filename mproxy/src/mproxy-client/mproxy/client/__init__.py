import pika

def proxy(meth_descr):
    '''Synthesise a method from the RPC method description.
    
    Requires that the class they are added to has a method `_rpc_call`
    which actually sends and gets raw bytes we can deal with.
    '''
    
    def call(self, *args, **kwargs):
        payload = meth_descr.serialise_args(*args, **kwargs)
        response = self._rpc_call(meth_descr.name, payload)
        return meth_descr.deserialise_result(response)
    call.__doc__ = meth_descr.doc
    call.__name__ = meth_descr.name
    return call

class Client:
    
    from mproxy.api import API
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

    def __init__(
            self, name, connection,
            exchange_name='machine_proxy'):

        self.name = name
        self.connection = connection
        self.exchange_name = exchange_name

        self.channel = connection.channel()

        # Declare my response queue
        result = self.channel.queue_declare('', exclusive=True)
        self.callback_queue = result.method.queue
        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self._handle_response,
            auto_ack=True)

        self._req_responses = {}
        return

    def _handle_response(self, channel, method, props, body):
        corr_id = props.correlation_id
        assert self._req_responses is None, "No outstanding request with ID: %s" % corr_id
        assert props.content_type == 'text/json'
        assert props.content_encoding == 'utf-8'
        headers = props.headers
        success_flag = {
            'true': True,
            'false': False
            }[headers['success']]
        self._req_responses[corr_id] = (success_flag, body)

    def _rpc_call(self, method_name, payload):
        topic = '{}.{}'.format(self.name, method_name)
        corr_id = str(uuid.uuid4())
        self._req_responses[corr_id] = None
        self.channel.basic_publish(
            exchange=self.exchange_name,
            routing_key=topic,
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=corr_id,
                content_type='text/json',
                content_encoding='utf-8'
                ))
        # Poll until we have an answer
        while self._req_responses[corr_id] is None:
            self.connection.process_data_events()

        ok, body = self._req_responses.pop(corr_id)

        if not ok:
            raise ValueError(body)
        return body
