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
        for attr in self._JSON_ATTRS:
            setattr(self, attr, locals()[attr])
    pass
