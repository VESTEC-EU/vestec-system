import sys
sys.path.append("../")
from Database.machine import Machine
import pony.orm as pny
from .pbs_queue import PBSQueueProcessor
import fabric

class MachineConnectionFactory:
    def __init__(self, configs):        
        self.configs = configs
        self._machine_cache = {}

    def _mk_fab_conn(self, conf):
        host = conf["hostname"]
        user = conf["username"]
        keyfile = conf["SSHkey"]

        return fabric.Connection(
            host, user=user, connect_kwargs={"key_filename": keyfile}
        )

    def _mk_fab_machine_connection(self, name, queue_system, conf):
        from .fabric_machine import FabricMachineConnection

        fabconn = self._mk_fab_conn(conf)
        d = conf["remote_base_dir"]
        return FabricMachineConnection(queue_system, fabconn, d)

    def _mk_openssh_machine_connection(self, name, queue_system, conf):
        from .openssh_machine import OpenSSHMachineConnection

        d = conf["remote_base_dir"]
        return OpenSSHMachineConnection(queue_system, conf["hostname"], conf["remote_base_dir"])

    def _mk_dummy_machine_connection(self, name, queue_system, conf):
        from .dummy_machine import DummyMachineConnection

        return DummyMachineConnection(name)

    def getConfiguration(self, name):
        try:
            return self.configs[name]
        except KeyError:
            print('Unknown connection name '+ name)
            raise

    @pny.db_session
    def __call__(self, name):
        stored_machine=Machine.get(machine_name=name)
        if stored_machine is None:
            print("Unknown connection name " + name)
            raise
        else:
            if stored_machine.test_mode:
                return self._mk_dummy_machine_connection(name, self.getConfiguration(name))
            else:                
                if name in self._machine_cache:
                    return self._machine_cache[name]
                else:
                    conf = self.getConfiguration(name)
                    # Choose a factory function based on type
                    ff = {
                        "fabricssh": self._mk_fab_machine_connection,
                        "openssh": self._mk_openssh_machine_connection,
                        "dummy": self._mk_dummy_machine_connection,
                    }[conf["type"]]
                    machine = ff(name, PBSQueueProcessor(), conf) #need queue system for this and dummy!
                    self._machine_cache[name] = machine
                    return machine

    pass
