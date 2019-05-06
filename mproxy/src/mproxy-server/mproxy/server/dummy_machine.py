import io
import logging
from mproxy.core.model import CmdResult
from .throttle import ThrottlableMixin, throttle

log = logging.getLogger(__name__)

class DummyMachineConnection(ThrottlableMixin):
    '''Don't do anything except log operations and return dummy data'''
    def __init__(
            self, name,
            min_wait_ms=1, max_wait_ms=2**15,
            get=b'Some data',
            cwd='/home/vestec',
            ls=['README.md']
            ):
        self.name = name
        super().__init__(min_wait_ms, max_wait_ms)
        self._get = get
        self._cwd = cwd
        self._ls = ls

    @throttle
    def run(self, command, env=None):
        log.info("%s.run(%s)", self.name, command)
        return CmdResult(command=command, env=env)
    @throttle
    def put(self, src_bytes, dest):
        log.info("%s.put(%d B -> %s)", self.name, len(src_bytes), dest)

    @throttle
    def get(self, src):
        log.info("%s.get(%s)", self.name, src)
        return self._get

    @throttle
    def cd(self, dirname):
        log.info("%s.cd(%s)", self.name, dirname)

    @throttle
    def getcwd(self):
        log.info("%s.getcwd()", self.name)
        return self._cwd

    @throttle
    def ls(self, dirname="."):
        log.info("%s.ls(%s)", self.name, dirname)
        return self._ls

    @throttle
    def mkdir(self, dirname):
        log.info("%s.mkdir(%s)", self.name, dirname)

    @throttle
    def rm(self, filename):
        log.info("%s.rm(%s)", self.name, filename)

    @throttle
    def rmdir(self, dirname):
        log.info("%s.rmdir(%s)", self.name, dirname)

    @throttle
    def mv(self, src, dest):
        log.info("%s.mv(%s -> %s)", self.name, src, dest)

def DummyMachineConnectionFactory(name):
    return DummyMachineConnection(name)
