import pytest
import asyncio

from mproxy.server.runner import ServerRunner
from mproxy.client import Client
from mproxy.core import ConfDict

# Filter out warning from paramiko as it will be fixed in an upcoming
# release
pytestmark = pytest.mark.filterwarnings(
    "ignore:Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated"
)


@pytest.fixture
def conf_for_dummy_machine(rabbit_temp_vhost):
    names = ("test",)
    conf = ConfDict(
        # fmt: off
        "testing_data",
        {
            "machines": {
                "test": {
                    "type": "dummy"
                }
            },
            "amqp": rabbit_temp_vhost
        }
    )
    return conf, names


@pytest.fixture
async def dummy_client(conf_for_dummy_machine):
    conf, names = conf_for_dummy_machine
    runner = ServerRunner(conf, names)
    await runner.start()
    client = await Client.create(names[0], runner.connection)
    yield client
    await client.disconnect()
    await runner.stop()


@pytest.mark.asyncio
async def test_dummy(dummy_client):
    cwd = await dummy_client.getcwd()
    assert cwd == "/home/vestec"


@pytest.mark.asyncio
async def test_log_only(dummy_client, logstore):
    await dummy_client.put(b"hello", "greeting.txt")
    assert len(logstore) == 1
    msg = logstore[0]
    assert (msg[0] % msg[1]) == "test.put(5 B -> greeting.txt)"

    results = await asyncio.gather(
        dummy_client.cd("ignored"),
        dummy_client.mkdir("ignored"),
        dummy_client.rm("ignored"),
        dummy_client.rmdir("ignored"),
        dummy_client.mv("ignored", "ignored"),
    )
    for r in results:
        assert r is None
    assert len(logstore) == 6


@pytest.mark.asyncio
async def test_run(dummy_client, logstore):
    cmd = "qstat"
    env = {"PBS_VAR": "value"}

    result = await dummy_client.run(cmd, env=env)
    assert result.command == cmd
    assert result.env == env
    assert result.exited == 0
    assert len(logstore) == 1


@pytest.mark.asyncio
async def test_ls_kwargs(dummy_client, logstore):
    assert await dummy_client.ls("ignored") == ["README.md"]
    assert await dummy_client.ls(dirname="ignored") == ["README.md"]
    assert await dummy_client.ls() == ["README.md"]

    assert len(logstore) == 3


@pytest.mark.asyncio
async def test_returning(dummy_client, logstore):
    assert await dummy_client.get("irrelevant/filename") == b"Some data"
    assert await dummy_client.getcwd() == "/home/vestec"
    assert await dummy_client.ls() == ["README.md"]

    assert len(logstore) == 3
