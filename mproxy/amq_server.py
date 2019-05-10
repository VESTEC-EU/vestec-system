#!/usr/bin/env python
"""Help in running an AMQP server via docker for testing"""

import os.path
import docker
import uuid
import time
import json
from contextlib import contextmanager

CONF_FILE_NAME = os.path.join(os.path.dirname(__file__), "test_amq_server.json")


def start():
    client = docker.from_env()
    rabbit_container_name = "rabbitmq:3.7-management-alpine"
    username = "pytest"
    password = uuid.uuid4().hex

    container = client.containers.run(
        rabbit_container_name,
        auto_remove=True,
        detach=True,
        publish_all_ports=True,
        environment={
            "RABBITMQ_DEFAULT_USER": username,
            "RABBITMQ_DEFAULT_PASS": password,
        },
    )
    # Wait until the Rabbit server is ready
    while container.logs(stdout=True, tail=10).find(b"Server startup complete") == -1:
        time.sleep(0.1)
    # Refresh container attributes
    container.reload()
    ports = container.attrs["NetworkSettings"]["Ports"]

    # Create a suitable config dict
    conf_data = {
        "id": container.id,
        "password": password,
        "username": username,
        "hostname": "localhost",
        "port": int(ports["5672/tcp"][0]["HostPort"]),
        "mgmt_port": int(ports["15672/tcp"][0]["HostPort"]),
    }

    return conf_data


def stop(cont_id):
    client = docker.from_env()
    container = client.containers.get(cont_id)
    container.stop()


def read():
    with open(CONF_FILE_NAME) as f:
        return json.load(f)


def do_command(cmd):
    if cmd == "start":
        assert not os.path.exists(CONF_FILE_NAME)
        conf = start()
        with open(CONF_FILE_NAME, "w") as f:
            json.dump(conf, f, indent=4)
    elif cmd == "stop":
        assert os.path.exists(CONF_FILE_NAME)
        conf = read()
        stop(conf["id"])
        os.remove(CONF_FILE_NAME)


@contextmanager
def temp_container():
    conf = start()
    yield conf
    stop(conf["id"])


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(
        description="Start or stop a Dockerised AMQ server for testing"
    )
    p.add_argument("command", choices=("start", "stop"))
    args = p.parse_args()
    do_command(args.command)
