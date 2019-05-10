# VESTEC mproxy

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

An asynchronous RPC-over-AMQP proxy for interacting with batch machines.

This consists of three packages:

* `mproxy-client`
* `mproxy-server`
* `mproxy-core`

## Install

I strongly recommend creating a virtual environment for this. Once you
have it, install dev dependencies with:

```
pip install -r dev-requirements
```

Then you can install the client and/or server packages with, e.g.
```
cd src/mproxy-server
poetry install
```

You can ensure the code style using
[Black](https://black.readthedocs.io/en/latest/):
```
black .
```

## Architecture

The server should have declared a topic exchange (default `mproxy`)
and queues corresponding to the configured names of machines that it
is proxying, binding the queue(s) to the topic exchange such that each
queue gets all messages for its machine.

The client library allows you to create a `Client` object that has
methods corresponding to the API in `mproxy.core.api`. It forwards the
method name, machine name, and arguments to a topic exchange on an AMQ
server (the message topic is `{machine name}.{method name}`) and will
await a reply (on a dedicated, temporary reply queue). The client also
subscribes a method to be called on receiving a reply message.

Suppose the client wants to call the `run` method on a machine
`hpc`. The client first checks the arguments, serialises them, and
create a message:

```
reply_to: $REPLY_QUEUE
correlation_id: $TAG
content_type: application/json
content_encoding: utf-8
body: $SERIALISED_ARGS
```

which it publishes to the exchange with a routing key `hpc.run`. The
client also creates a future to hold the eventual return value, stores
this internally, and awaits the value.

The AMQ exchange passes this to the `hpc` queue, which delivers this
to the server and triggers a callback. The server validated the
routing key and content, then looks up the requested method, and
deserialises the arguments. The server creates or reuses a connection
manager object for the `hpc` machine and calls the corresponding
method with the arguments.

The connection manager throttles (i.e. rate limits) connections to the
machine to ensure we don't DOS them. It enforces a minimum time
between connections and this ramps up as it receives more connection
attempts (a bounded version of exponential backoff).

The connection manager performs the operation on the remote machine
and returns a result. The RPC server checks the result, serialises it,
and creates a message:

```
correlation_id: $TAG
content_type: application/json
content_encoding: utf-8
headers:
    success: true
body: $SERIALISED_RESULT
```
which it publishes to the default exchange on the AMQP server with a
routing key `$REPLY_QUEUE`.

The client response callback is triggered which looks up the future
from the correlation identifier. We set the value of the future which
then schedules its waiters (i.e. the original RPC method call) to
run. This deserialises the result and returns it to the caller.


## Server

* Install `mproxy-server` package
* Write a configuration YAML file e.g. `mproxy.yml`:
```
amqp:
    username: guest
	password: guest
	hostname: localhost

machines:
    test:
	    type: dummy

	hpc:
        type: ssh
		hostname: login.hpc.university.ac.uk
		username: vestec
		SSHkey: ~/.ssh/id_rsa
```

* Run the server: `python -m mproxy.server.main`

You can set the configuration file with the `-c`/`--config` flag,
e.g. `python -m mproxy.server.main -c /etc/vestec-mproxy.yml`

By default the server accept requests for all the machine names in the
configuration file but you can restrict it by listing them on the
command line: `python -m mproxy.server.main test`


## Client

Note: the client is currently implemented with coroutines and must be
run within an event loop. See python docs for
[coroutine objects](https://docs.python.org/3.7/reference/datamodel.html?highlight=coroutine#coroutine-objects)
and the
[asyncio standard library package](https://docs.python.org/3/library/asyncio.html).

```
from mproxy.client import Client
async def example():
    connection = await aio_pika.connect({
        "hostname": "localhost",
        "username": "guest",
        "password": "guest",
    })
    client = await Client.create("hpc", connection)
    cwd = await client.getcwd()
    print(cwd)
```

## Testing

You can run the tests with `pytest`. The `mproxy-core` unit tests can
run with [tox](https://tox.readthedocs.io/en/latest/).

The integration tests (in `mproxy/tests`) require a running AMQP
server. The tests can attempt to create one via Docker, but you must
have previously pulled the image
`rabbitmq:3.7-management-alpine`. Since starting the server is slow
(~10 s) you may choose to start one manually - `amq_server.py` will
help:

```
$ ./amq_server.py start
# waits 5-10 s
$ pytest
========================= test session starts =========================
platform darwin -- Python 3.7.3, pytest-4.4.1, py-1.8.0, pluggy-0.11.0
rootdir: .vestec-wp5/mproxy
plugins: asyncio-0.10.0
collected 25 items                                                    

src/mproxy-core/tests/test_conf.py .....                        [ 20%]
src/mproxy-core/tests/test_rpc.py ...                           [ 32%]
src/mproxy-core/tests/test_serialisation.py ....                [ 48%]
src/mproxy-server/tests/test_dummy_machine.py ...               [ 60%]
src/mproxy-server/tests/test_throttle.py .....                  [ 80%]
tests/test_dummy.py .....                                       [100%]

====================== 25 passed in 1.04 seconds ======================
$ ./amq_server.py stop
```

