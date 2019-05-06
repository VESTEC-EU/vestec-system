from mproxy.server.dummy_machine import DummyMachineConnection


class logstore:
    def __init__(self, monkeypatch):
        from mproxy.server.dummy_machine import log

        self.real = log
        monkeypatch.setattr(log, "info", self.log)
        self.messages = []

    def log(self, msg, *args, **kwargs):
        self.messages.append((msg, args, kwargs))


def test_log_only(monkeypatch):
    log = logstore(monkeypatch)
    machine = DummyMachineConnection("hello")

    machine.put(b"hello", "greeting.txt")
    assert len(log.messages) == 1
    msg = log.messages[0]
    assert (msg[0] % msg[1]) == "hello.put(5 B -> greeting.txt)"

    machine.cd("ignored")
    machine.mkdir("ignored")
    machine.rm("ignored")
    machine.rmdir("ignored")
    machine.mv("ignored", "ignored")
    assert len(log.messages) == 6


def test_run(monkeypatch):
    log = logstore(monkeypatch)
    machine = DummyMachineConnection("hello", get=b"expected")
    cmd = "qstat"
    env = {"PBS_VAR": "value"}

    result = machine.run(cmd, env=env)
    assert result.command == cmd
    assert result.env == env
    assert result.exited == 0


def test_returning(monkeypatch):
    log = logstore(monkeypatch)
    machine = DummyMachineConnection(
        "hello", get=b"expected data", cwd="expected/dir", ls=["expected.file"]
    )

    assert machine.get("irrelevant/filename") == b"expected data"
    assert machine.getcwd() == "expected/dir"
    assert machine.ls() == ["expected.file"]

    assert len(log.messages) == 3
