import inspect
import json
from .serialisation import JsonObjHelper, JsonTypeError


class RpcMethod:
    """Encapsulate argument/result (de)serialisation for a function
    based on a type-annotated function signature and name.
    """

    def __init__(self, name, signature, doc=None):
        if (
            signature.return_annotation is None
            or signature.return_annotation is signature.empty
        ):
            signature = signature.replace(return_annotation=type(None))
        self.name = name
        self.sig = signature
        self.doc = doc

    @classmethod
    def from_function(cls, func):
        """Factory function from a function"""
        return cls(func.__name__, inspect.signature(func), func.__doc__)

    def call_with(self, obj, arg_dict):
        """Apply a dictionary of arguments, probably from
        deserialise_args, to an object assuming that it has a method
        with our name and signature (less type annotations).
        """
        bound = self.sig.bind(**arg_dict)
        method = getattr(obj, self.name)
        return method(*bound.args, **bound.kwargs)

    def serialise_args(self, *args, **kwargs):
        """Turn this method's args+kwargs into bytes (UTF-8)"""
        bound = self.sig.bind(*args, **kwargs)
        json_obj = {}
        for name, param in self.sig.parameters.items():
            try:
                py_obj = bound.arguments[name]
            except KeyError:
                continue

            if not isinstance(py_obj, param.annotation):
                raise TypeError(
                    'Argument "{}" not of type "{}"'.format(name, param.annotation)
                )

            json_obj[name] = JsonObjHelper.py2j(py_obj)

        return json.dumps(json_obj).encode()

    def deserialise_args(self, buf):
        """Turn raw bytes from the wire to a dictionary of arguments
        matching our function signature, that can be applied to the real
        method.
        """
        dct = json.loads(buf)
        arg_dict = {}
        for name, param in self.sig.parameters.items():
            json_obj = dct.pop(name, param.default)
            if json_obj is param.empty:
                raise ValueError("Missing required argument: %s" % name)
            arg_dict[name] = JsonObjHelper.j2py(param.annotation, json_obj)

        if len(dct):
            raise ValueError(
                "Unknown argument(s): " + ", ".join('"%"' % k for k in dct.keys())
            )
        return arg_dict

    def serialise_result(self, pyobj):
        """Turn an actual result object into bytes (UTF-8)"""
        rt = self.sig.return_annotation
        if not isinstance(pyobj, rt):
            raise TypeError('Return value not of type "{}"'.format(rt))
        jobj = JsonObjHelper.py2j(pyobj)
        return json.dumps(jobj).encode()

    def deserialise_result(self, buf):
        """Turn raw bytes from the wire to an object of return
        annotation type.
        """
        json_obj = json.loads(buf)
        try:
            return JsonObjHelper.j2py(self.sig.return_annotation, json_obj)
        except JsonTypeError as e:
            # TypeErrors from j2py should be ValueError really
            raise ValueError("reconstructed types do not match") from e

    pass


rpcmethod = RpcMethod.from_function
