class ConfDict:
    '''Simple dictionary wrapper for configuration data that knows where
    it lives in the file for better errors.

    Keys must be strings, not arbitrary hashables
    '''
    def __init__(self, parent, data, my_key=None):
        if my_key is not None:
            assert isinstance(my_key, str), "Keys must be strings"

        self._key = my_key
        if my_key is None:
            self._path = parent
            self._sep = ':'
        else:
            self._path = parent._path + parent._sep + my_key
            self._sep = '.'

        self._data = {}
        for key, val in data.items():
            self._data[key] = ConfDict(self, val, key) if isinstance(val, dict) else val

    @classmethod
    def from_yaml(cls, filename):
        import yaml
        with open(filename) as f:
            return cls(filename, yaml.safe_load(f))

    @classmethod
    def from_json(cls, filename):
        import json
        with open(filename) as f:
            return cls(filename, json.load(f))

    def __getitem__(self, key):
        assert isinstance(key, str)
        try:
            return self._data[key]
        except KeyError as e:
            raise KeyError("ConfDict '{}' has no key '{}'".format(self._path, key)) from e

    def __getattr__(self, key):
        try:
            return self._data[key]
        except KeyError as e:
            raise AttributeError("ConfDict '{}' has no key '{}'".format(self._path, key)) from e

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def keys(self):
        return self._data.keys()
    def values(self):
        return self._data.values()
    def items(self):
        return self._data.items()
