from mproxy.server.dummy_machine import DummyMachineConnection


def test_log_only(logstore):
    machine = DummyMachineConnection("hello")

    machine.put(b"hello", "greeting.txt")
    assert len(logstore) == 1
    msg = logstore[0]
    assert (msg[0] % msg[1]) == "hello.put(5 B -> greeting.txt)"

    machine.cd("ignored")
    machine.mkdir("ignored")
    machine.rm("ignored")
    machine.rmdir("ignored")
    machine.mv("ignored", "ignored")
    assert len(logstore) == 6


def test_run(logstore):
    machine = DummyMachineConnection("hello", get=b"expected")
    cmd = "qstat"
    env = {"PBS_VAR": "value"}

    result = machine.run(cmd, env=env)
    assert result.command == cmd
    assert result.env == env
    assert result.exited == 0
    assert len(logstore) == 1


def test_returning(logstore):
    machine = DummyMachineConnection(
        "hello", get=b"expected data", cwd="expected/dir", ls=["expected.file"]
    )

    assert machine.get("irrelevant/filename") == b"expected data"
    assert machine.getcwd() == "expected/dir"
    assert machine.ls() == ["expected.file"]

    assert len(logstore) == 3
