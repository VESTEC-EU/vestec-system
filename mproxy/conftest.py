import pytest
import os.path
import uuid
import requests
import json


@pytest.fixture
def logstore(monkeypatch):
    """Intercept the dummy_machine log"""
    from mproxy.server.dummy_machine import log as real

    messages = []

    def log(msg, *args, **kwargs):
        messages.append((msg, args, kwargs))

    monkeypatch.setattr(real, "info", log)
    yield messages
    return


@pytest.fixture(scope="session")
def rabbit_container():
    """Start an AMQP server containter, yield connection data, and
    shutdown the container.
    """
    from amq_server import CONF_FILE_NAME, start, stop, read

    if os.path.exists(CONF_FILE_NAME):
        yield read()
    else:
        conf = start()
        yield conf
        stop(conf["id"])


@pytest.fixture
def rabbit_temp_vhost(rabbit_container):
    """Create an ephemeral vhost and user for testing, yield connection
    data, then delete.
    """
    mgmt_conf_data = rabbit_container
    vhost, up = str(uuid.uuid4()).split("-", 1)
    tmp_u, tmp_p = up.rsplit("-", 1)
    temp_conf = {
        "vhost": vhost,
        "username": tmp_u,
        "password": tmp_p,
        "hostname": mgmt_conf_data["hostname"],
        "port": mgmt_conf_data["port"],
    }

    sesh = requests.Session()
    sesh.auth = (mgmt_conf_data["username"], mgmt_conf_data["password"])
    base_url = "http://{hostname}:{mgmt_port:d}/api".format(**mgmt_conf_data)

    # Create vhost
    vhost_url = "{base_url}/vhosts/{vhost}".format(**locals())
    resp = sesh.put(vhost_url)
    assert resp.ok, str(resp)

    # Create user
    user_url = "{base_url}/users/{tmp_u}".format(**locals())
    resp = sesh.put(user_url, data=json.dumps({"password": tmp_p, "tags": ""}))
    assert resp.ok, str(resp)

    # grant permissions
    permission_url = "{base_url}/permissions/{vhost}/{tmp_u}".format(**locals())
    permission_data = {"configure": ".*", "write": ".*", "read": ".*"}
    resp = sesh.put(permission_url, data=json.dumps(permission_data))
    assert resp.ok, str(resp)

    yield temp_conf

    # Delete user and vhost
    resp = sesh.delete(user_url)
    assert resp.ok, str(resp)
    resp = sesh.delete(vhost_url)
    assert resp.ok, str(resp)
