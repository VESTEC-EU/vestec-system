import argparse
import asyncio

from mproxy.api.conf import ConfDict


async def main():
    p = argparse.ArgumentParser(description="Machine Proxy server")
    p.add_argument("--config", default="mproxy.yml", help="configuration file")
    p.add_argument(
        "names",
        nargs="*",
        help="names of configured machines to proxy, none implies all in the config",
    )

    args = p.parse_args()

    config = ConfDict.from_yaml(args.config)
    names = args.names if len(args.names) else list(config["machines"].keys())

    from .runner import ServerRunner

    runner = ServerRunner(config, names)
    await runner.start()


if __name__ == "__main__":
    asyncio.run(main())

