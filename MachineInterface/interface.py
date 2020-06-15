import sys
sys.path.append("../")
from Database import initialiseDatabase
import argparse
import asyncio
import signal

from mproxy.core.conf import ConfDict
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
    p = argparse.ArgumentParser(description="Machine Proxy server")
    p.add_argument("--config", default="machines.yml", help="configuration file")
    p.add_argument(
        "names",
        nargs="*",
        help="names of configured machines to proxy, none implies all in the config",
    )

    args = p.parse_args()

    config = ConfDict.from_yaml(args.config)
    for n in args.names:
        assert (
            n in config["machines"]
        ), "Requested machine name '{}' not configured".format(n)

    names = args.names if len(args.names) else list(config["machines"].keys())    

    initialiseDatabase()
    runner = ServerRunner(config, names)    
    await runner.start()
    print("Started machine interface")
    await wait_for_interrupt()

if __name__ == "__main__":
    asyncio.run(main())
