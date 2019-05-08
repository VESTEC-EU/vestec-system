import pika
from .machine import MachineConnectionFactory
from .rpc_server import RpcServer

class ServerRunner:
    def __init__(self, config, names):
        self.config = config
        self.names = names
        self.mc_factory = MachineConnectionFactory(config["machines"])

    def make_mq_connection_params(self):
        mq_conf = self.config["amqp"]

        default = pika.ConnectionParameters._DEFAULT
        try:
            pw = mq_conf["password"]
        except KeyError:
            pw_file = mq_conf["password_file"]
            with open(pw_file) as f:
                pw = f.read()
            pass

        mq_cred = pika.PlainCredentials(mq_conf["username"], pw)

        return pika.ConnectionParameters(
            mq_conf["hostname"],
            port=mq_conf.get("port", default),
            virtual_host=mq_conf.get("virtual_host", default),
            credentials=mq_cred,
        )

    def start(self):
        mq_conn = pika.BlockingConnection(self.make_mq_connection_params())

        servers = {}
        for name in self.names:
            servers[name] = RpcServer(name, self.mc_factory, mq_conn)

        if len(self.names) <= 1:
            servers[self.names[0]].start()
        else:
            from threading import Thread

            threads = [Thread(s.start) for s in servers]
            [t.start() for t in threads]
            [t.join() for t in threads]
