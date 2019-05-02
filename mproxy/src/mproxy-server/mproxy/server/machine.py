
class MachineConnectionFactory:
    def __init__(self, configs):
        self.configs = configs
        self._machine_cache = {}

    def _mk_fab_conn(self, conf):
        host = conf['hostname']
        user = conf['username']
        keyfile = conf['SSHkey']

        return fabric.Connection(
            host,
            user=user,
            connect_kwarg={
                'key_filename': keyfile
                }
            )

    def _mk_fab_machine_connection(self, name, conf):
        from fabric_machine import FabricMachineConnection
        fabconn = self._mk_fab(conf)
        d = conf['remote_base_dir']
        return FabricMachineConnection(fabconn, d)

    def _mk_dummy_machine_connection(self, name, conf):
        from dummy_machine import DummyMachineConnection
        return DummyMachine(name)

    def __call__(self, name):
        try:
            machine = self._machine_cache[name]
        except KeyError:
            try:
                conf = self.configs[name]
            except KeyError:
                log.error('Unknown connection name "%s"', name)
                raise
        # Choose a factory function based on type
        ff = {
            'ssh': self._mk_fab_machine_connection,
            'dummy': self._mk_dummy_machine_connection
            }[conf['type']]
        machine = ff(name, conf)
        self._machine_cache[name] = machine
        return machine

    pass
