import asyncio
import aio_pika
import sys
sys.path.append("../")
from .machine import MachineConnectionFactory
import pony.orm as pny
from Database.machine import Machine
from .rpc_server import RpcServer
from ..core.connect import aio_pika_connect_params
import os
import time

class ServerRunner:
    @pny.db_session
    def __init__(self):        
        self.names = []
        configuredMachines=pny.select(configuredMachines for configuredMachines in Machine)
        for machine in configuredMachines:
            self.names.append(machine.machine_name)
        self.mc_factory = MachineConnectionFactory()
        self.connection = None

    async def start(self, loop=None):
        """Create a connection and start all the servers listening to
        it.
        """
        if "VESTEC_RMQ_SERVER" in os.environ:
            host = os.environ["VESTEC_RMQ_SERVER"]            
        else:
            print("Environment variable VESTEC_RMQ_SERVER not set. Defaulting to `localhost`")
            host="localhost"

        for i in range(5):
            print(" [*] Opening connection to RabbitMQ server")
            try:
                self.connection = await aio_pika.connect(loop=loop, host=host)
            except:
                if i<4:
                    print("Cannot connect to RabbitMQ server. Will try again in 5 seconds...")
                    time.sleep(5)
                else:
                    print("Cannot create connection to AMQP server... Maybe it's down?")
                    raise
            else:
                break

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
