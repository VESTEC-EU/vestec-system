import asyncio
import aio_pika
from .machine import MachineConnectionFactory
from .rpc_server import RpcServer
from ..core.connect import aio_pika_connect_params


class ServerRunner:
    def __init__(self, config, names):
        self.config = config
        self.names = names
        self.mc_factory = MachineConnectionFactory(config["machines"])
        self.connection = None

    async def start(self, loop=None):
        """Create a connection and start all the servers listening to
        it.
        """
        self.connection = await aio_pika.connect(
            loop=loop, host="localhost"
        )

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
