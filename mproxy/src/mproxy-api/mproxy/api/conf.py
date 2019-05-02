class ConfDict:
    '''Simple dictionary wrapper for configuration data that knows where
    it lives in the file for better errors.
    '''
    def __init__(self, parent, data, my_key=None):
        self._parent = parent
        self._data = {}
        self._key = my_key
        for key, val in data.items():
            self._data[key] = ConfDict(self, val, key) if isinstance(val, dict) else val

    def from_yaml(cls, filename):
        import yaml
        with open(filename) as f:
            return cls(filename, yaml.load(f))

    def from_json(cls, filename):
        import json
        with open(filename) as f:
            return cls(filename, json.load(f))

    def _get_path(self):
        if self._key is None:
            return self._parent
        else:
            sep = ':' if self._parent.key is None else '.'
            return self._parent._get_path() + sep + self._key

    def __getitem__(self, key):
        try:
            return self._data[key]
        except KeyError:
            my_path = self._get_path()
            sep = ':' if self._key is None else '.'
            raise KeyError(my_path + sep + key)

    def __getattr__(self, key):
        try:
            return self._data[key]
        except KeyError:
            raise AttributeError("ConfDict '{}' has no key '{}'".format(self._get_path(), key))

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
