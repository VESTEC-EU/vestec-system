from .rpc import rpcmethod
from .serialisation import JsonSerialisable

class CmdResult(JsonSerialisable):
    _JSON_ATTRS = set((
        'stdout',
        'stderr',
        'encoding',
        'command',
        'shell',
        'env',
        'exited',
        'pty',
        'hide'
        ))
    def __init__(self, stdout='', stderr='', encoding=None, command='', shell='', env=None, exited=0, pty=False, hide=()):
        for k, v in kwargs.items():
            setattr(self, k, v)
    pass

class API:
    @rpcmethod
    def run(cmd : str, env : dict=None) -> CmdResult:
        '''Run a command on the remote server'''
        return
    @rpcmethod
    def put(src_bytes : bytes, dest : str) -> None:
        return
    @rpcmethod
    def get(src : str) -> bytes:
        pass
    @rpcmethod
    def cd(dirname : str) -> None:
        pass
    @rpcmethod
    def getcwd() -> str:
        pass
    @rpcmethod
    def ls(dirname=".") -> list:
        pass
    @rpcmethod
    def mkdir(d : str) -> None:
        pass
    @rpcmethod
    def rm(filename : str) -> None:
        pass
    @rpcmethod
    def rmdir(dirname : str) -> None:
        pass
    @rpcmethod
    def mv(src : str, dest : str) -> None:
        pass
    pass
