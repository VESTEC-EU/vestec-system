import py.test
import json
import yaml
import io

from mproxy.api.conf import ConfDict

sample_data = {
    'greeting': 'hello',
    'person': 'world',
    'subdict': {
        'float': 1.0,
        'int': 1,
        'bool': True,
        'list': [
            0.0,
            0,
            False
            ]
        }
    }

class wrapper:
    def __init__(self, data, coder):
        self.data = data
        self.encoded = coder(sample_data)

    def open(self, *args, **kwargs):
        return io.StringIO(self.encoded)
    pass

def assert_dict_equiv(cd, d):
    ak = set(cd.keys())
    bk = set(d.keys())
    assert ak == bk, 'differing keys'

    for key in cd.keys():
        cdval = cd[key]
        dval = d[key]
        if isinstance(cdval, ConfDict):
            assert_dict_equiv(cdval, dval)
        else:
            assert cdval == dval

def test_load_yaml(monkeypatch):
    wr = wrapper(sample_data, yaml.dump)
    monkeypatch.setitem(__builtins__, 'open', wr.open)

    conf = ConfDict.from_yaml('filename_irrelevant.yml')
    assert_dict_equiv(conf, sample_data)
    
def test_load_json(monkeypatch):
    wr = wrapper(sample_data, json.dumps)
    monkeypatch.setitem(__builtins__, 'open', wr.open)

    conf = ConfDict.from_yaml('filename_irrelevant.yml')
    assert_dict_equiv(conf, sample_data)
    
def test_attr_access():
    conf = ConfDict('none', sample_data)
    item = conf.subdict.list
    assert item == sample_data['subdict']['list']

def test_paths():
    conf = ConfDict('none', sample_data)
    assert conf.subdict._path == 'none:subdict'

def test_throwing():
    conf = ConfDict('none', sample_data)
    try:
        conf.subdict['missing']
    except KeyError as e:
        assert isinstance(e.__cause__, KeyError)
        pass
    else:
        assert False, 'Should have thrown KeyError'

    try:
        conf.subdict.missing
    except AttributeError as e:
        assert isinstance(e.__cause__, KeyError)
    else:
        assert False, 'Should have thrown AttributeError'

