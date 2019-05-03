from mproxy.api.rpc import RpcMethod
from pytest import raises

class Wrapper:
    def __init__(self, func):
        self.called = False        
        def wrapper(*args, **kwargs):
            self.called = True
            return func(*args, **kwargs)
        fname = func.__name__
        setattr(self, fname, wrapper)
    pass

def test_nullary():
    def null():
        '''Most useless function'''
        return
    meth = RpcMethod.from_function(null)

    # No arguments - but pack them
    sa = meth.serialise_args()
    assert sa == b'{}'
    
    # Any args should fail
    with raises(TypeError):
        meth.serialise_args(1)
    with raises(TypeError):
        meth.serialise_args(foo='bar')

    # And unpack
    da = meth.deserialise_args(sa)
    assert da == {}
    # error on unexpected args
    with raises(ValueError):
        meth.deserialise_args(b'{"foo": "bar"}')

    tobj = Wrapper(null)
    res = meth.call_with(tobj, da)
    assert tobj.called

    with raises(TypeError):
        res = meth.call_with(tobj, {"foo": "bar"})

    # Return is None
    sr = meth.serialise_result(res)
    assert sr == b'null'
    # Error on not-None
    with raises(TypeError):
        meth.serialise_result('Failure is guaranteed!')

    # unpack
    dr = meth.deserialise_result(sr)
    assert dr is None
    with raises(ValueError):
        meth.deserialise_result(b'{}')

def roundtrip_compare(function, *args, **kwargs):
    '''Take a function and some arguments, round trip args, call
    function, round trip result, and compare to f(args)
    '''
    meth = RpcMethod.from_function(function)
    sa = meth.serialise_args(*args, **kwargs)
    da = meth.deserialise_args(sa)
    res = meth.call_with(Wrapper(function), da)
    sr = meth.serialise_result(res)
    dr = meth.deserialise_result(sr)
    assert dr == function(*args, **kwargs)

def test_simple():
    def list_prod(n : int) -> list:
        return [n]*n
    roundtrip_compare(list_prod, 1)
    roundtrip_compare(list_prod, 10)

    # A few more detailed tests!
    meth = RpcMethod.from_function(list_prod)

    # Pack arguments
    sa = meth.serialise_args(3)
    assert sa == b'{"n": 3}'

    # Arg of wrong type must fail
    with raises(TypeError):
        meth.serialise_args([3])
    # Wrong number of args too
    with raises(TypeError):
        meth.serialise_args(2, 3)
    # Calling by wrong kw too
    with raises(TypeError):
        meth.serialise_args(m=2)

    # And unpack (as dictionary)
    da = meth.deserialise_args(sa)
    assert da == {'n': 3}

    # Create the test object with list_prod method
    tobj = Wrapper(list_prod)
    res = meth.call_with(tobj, da)
    assert res == [3, 3, 3]

    # Pack result
    sr = meth.serialise_result(res)
    # unpack
    dr = meth.deserialise_result(sr)
    assert dr == res

    # Check deserialisation fails if 'n' is missing
    with raises(ValueError):
        meth.deserialise_args(b'{}')

def test_complex():
    from test_serialisation import ComplexObject
    # object p has 2 children, c1, c2
    # object c1 has 1 child, g
    g = ComplexObject('g')
    c1 = ComplexObject('c1', children=(g,), binary=b'OOOOO')
    c2 = ComplexObject('c2', binary='Comment ça va? Très bien merci!'.encode('utf-8'))
    p = ComplexObject('p', children=(c1, c2))

    def count_kids(co : ComplexObject) -> int:
        return len(co.children) + sum(count_kids(ch) for ch in co.children)
    # Self tests
    assert count_kids(p) == 3

    roundtrip_compare(count_kids, p)
