import sys
sys.path.append("../")
from Database.machine import Machine
import pony.orm as pny
import fabric

class MachineConnectionFactory:
    def __init__(self, configs):        
        self.configs = configs
        self._machine_cache = {}
        self.machine_connections = { "fabricssh": self._mk_fab_machine_connection,
                                     "openssh": self._mk_openssh_machine_connection,
                                     "dummy": self._mk_dummy_machine_connection }

        self.queue_processors = { "pbs" : self._mk_pbs_queue_processor }

    def _mk_pbs_queue_processor(self):
        from .pbs_queue import PBSQueueProcessor

        return PBSQueueProcessor()

    def _mk_fab_conn(self, conf):
        host = conf["hostname"]
        user = conf["username"]
        keyfile = conf["SSHkey"]

        return fabric.Connection(
            host, user=user, connect_kwargs={"key_filename": keyfile}
        )    

    def _mk_fab_machine_connection(self, name, queue_system, machine, conf):
        from .fabric_machine import FabricMachineConnection

        fabconn = self._mk_fab_conn(conf)        
        return FabricMachineConnection(queue_system, fabconn, machine.base_work_dir)

    def _mk_openssh_machine_connection(self, name, queue_system, machine, conf):
        from .openssh_machine import OpenSSHMachineConnection
        
        return OpenSSHMachineConnection(queue_system, machine.host_name, machine.base_work_dir)

    def _mk_dummy_machine_connection(self, name, queue_system, machine, conf):
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
        elif stored_machine.enabled:        
            if stored_machine.test_mode:
                return self._mk_dummy_machine_connection(name, None, stored_machine, self.getConfiguration(name))
            else:                
                if name in self._machine_cache:
                    return self._machine_cache[name]
                else:
                    conf = self.getConfiguration(name)
                    # Choose a factory function based on type
                    if stored_machine.connection_type in self.machine_connections and stored_machine.scheduler in self.queue_processors:
                        selectedMachineMechanism=self.machine_connections[stored_machine.connection_type]
                        selectedQueueProcessor=self.queue_processors[stored_machine.scheduler]
                        createdMachineMechanism = selectedMachineMechanism(name, selectedQueueProcessor(), stored_machine, conf) 
                        self._machine_cache[name] = createdMachineMechanism
                        return createdMachineMechanism
                    else:
                        print("Error, either machine connection type or scheduler is not recognised")
                        raise
        else:
            print("Machine disabled, will not connect")
            raise

    pass
