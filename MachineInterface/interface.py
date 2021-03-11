import sys
sys.path.append("../")
from Database import initialiseDatabase
import argparse
import asyncio
import signal

from mproxy.server.runner import ServerRunner

async def wait_for_interrupt():
    loop = asyncio.get_event_loop()
    future = loop.create_future()
    loop.add_signal_handler(signal.SIGINT, future.set_result, None)
    try:
        await future
    finally:
        loop.remove_signal_handler(signal.SIGINT)


async def main():
    initialiseDatabase()
    runner = ServerRunner()    
    await runner.start()
    print("Started machine interface")
    await wait_for_interrupt()

if __name__ == "__main__":
    asyncio.run(main())
