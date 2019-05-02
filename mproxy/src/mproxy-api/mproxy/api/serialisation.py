'''
Help for JSON serialisation - converts between complex Python objects
and ones that the `json` module can handle.

'''
from base64 import b64decode, b64encode

class BytesConverter:
    '''Convert between bytes and base 64 encoded ASCII string'''
    @staticmethod
    def py2j(b):
        return b64encode(b).decode('ascii')
    @staticmethod
    def j2py(s):
        return b64decode(s)
    pass

class TupleConverter:
    '''Json treats tuples as lists'''
    @staticmethod
    def py2j(t):
        return [x for x in t]
    @staticmethod
    def j2py(t):
        return tuple(x for x in t)
    pass

class JsonObjHelper:
    '''Convert between known python objects and something that the json
    module can handle.

    Types must:
    - be the standard JSON known ones:
      * dict, list, str, float, bool, NoneType

    - have method `_to_json` and classmethod `_from_json`

    - be a key in CONVERTERS that maps to an object with py2j and j2py
      methods for converting.
    '''

    BUILTIN_TYPES = set((dict, list, str, int, float, bool, type(None)))
    CONVERTERS = {
        bytes: BytesConverter,
        tuple: TupleConverter
        }

    @classmethod
    def j2py(cls, out_cls, jobj):
        # No-op if JSON builtin
        if out_cls in cls.BUILTIN_TYPES:
            return jobj

        # Known special cases
        try:
            conv = cls.CONVERTERS[out_cls]
        except KeyError:
            pass
        else:
            return conv.j2py(jobj)

        # API objects that know about us
        try:
            return out_cls._from_json(jobj)
        except AttributeError:
            raise ValueError('Cannot reconstruct type: %s', out_cls)

    @classmethod
    def py2j(cls, pyobj):
        in_cls = type(pyobj)

        # No-op if JSON builtin
        if in_cls in cls.BUILTIN_TYPES:
            return pyobj

        # Known special cases
        try:
            conv = cls.CONVERTERS[in_cls]
        except KeyError:
            pass
        else:
            return conv.py2j(pyobj)

        # API objects
        try:
            return pyobj._to_json()
        except AttributeError:
            raise ValueError('Cannot serialise type: %s', type(pyobj))
    pass

class JsonSerialisable:
    '''Helper for serialising, just define a class attribute
    `_JSON_ATTRS` to be an iterable of strings
    '''

    @classmethod
    def _other_to_json(cls, obj):
        return {
            attr: JsobObjHelper.py2j(getattr(obj, attr)) for attr in cls._JSON_ATTRS
            }

    def _to_json(self):
        return self._other_to_json(self)

    @classmethod
    def _from_json(cls, jobj):
        '''This assumes that your class has a constructor accepting all
        attrs as keyword arguments.
        '''
        return cls(**jobj)
    pass
