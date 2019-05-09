import asyncio
import aio_pika
from .machine import MachineConnectionFactory
from .rpc_server import RpcServer

class ServerRunner:
    def __init__(self, config, names):
        self.config = config
        self.names = names
        self.mc_factory = MachineConnectionFactory(config["machines"])
        self.connection = None

    def make_mq_connection_params(self):
        mq_conf = self.config["amqp"]

        try:
            pw = mq_conf["password"]
        except KeyError:
            pw_file = mq_conf["password_file"]
            with open(pw_file) as f:
                pw = f.read()
            pass

        return {
            "login": mq_conf["username"],
            "password": pw,
            "host": mq_conf["hostname"],
            "port": mq_conf.get("port", 5672),
            "virtualhost": mq_conf.get("vhost", "/")
        }

    async def start(self, loop=None):
        '''Create a connection and start all the servers listening to
        it.
        '''
        self.connection = await aio_pika.connect(loop=loop, **self.make_mq_connection_params())

        self.servers = {
            name: RpcServer(name, self.mc_factory, self.connection)
            for name in self.names
        }

        await asyncio.gather(*(s.start() for s in self.servers.values()))

    async def stop(self):
        # Stop servers
        # disconnect
        await asyncio.gather(*(s.stop() for s in self.servers.values()))
        await self.connection.close()
