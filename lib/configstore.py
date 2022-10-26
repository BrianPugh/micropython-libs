"""Persistent key-value store for micropython.

* Dictionary-like interface.
* Saves happen automatically on write.
* Supports nested lists and dictionaries.
* Saves can be deferred by using context manager.

Example::

    from configstore import ConfigStore
    config = ConfigStore("settings.json")
    config["foo1"] = "bar1"  # Simple key/value store
    config["list_example"] = [1, 2, 3]  # lists work
    config["nested"] = {  # So do nested dictionaries.
        "foo2": "bar2"
    }

    config_reload = ConfigStore.load("settings.json")  # Load an existing config
    assert config_reload == config  # They should be the same.

    with config:  # defer writes until the contextmanager exits.
        config["a"] = 1
        config["b"] = 2
        config["c"] = 3


Typical Usecase::

    from configstore import ConfigStore
    config = ConfigStore("settings.json")
    config.merge({  # Populates unpopulated elements with default parameters.
        "name": "UNKNOWN",
        "id": 1234,
    })
    config.freeze_schema()

    print(f"Hello {config['name']}")
"""
import json
import os

try:
    from typing import Union
except ImportError:
    pass


class FrozenError(Exception):
    """Invalid operation on frozen WatchBase."""


class WatchBase:
    MERGE_STRATEGIES = {"ours", "theirs"}
    data: list | dict

    def __init__(self):
        self.parent = None
        self.key = None
        self._modified = False
        self.children = []
        self._frozen = False

    @classmethod
    def with_parent(cls, parent, *args, **kwargs):
        inst = cls(*args, **kwargs)
        inst.parent = parent
        parent.children.append(inst)
        return inst

    @property
    def modified(self):
        return self._modified

    @property
    def frozen(self):
        return self._frozen

    @modified.setter
    def modified(self, val):
        val = bool(val)
        self._modified = val
        self.modified_cb()
        # modified==True propagates up.
        # modified==False propagates down.
        if val:
            if self.parent:
                self.parent.modified = True
        else:
            for child in self.children:
                child.modified = False

    def modified_cb(self):
        pass

    def __repr__(self):
        return repr(self.data)

    def __len__(self):
        return len(self.data)

    def __contains__(self, value):
        return value in self.data

    def __iter__(self):
        for val in self.data:
            yield val

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        value = self._process_value(value)

        if self._frozen and isinstance(value, WatchBase):
            raise FrozenError("Cannot overwrite dict/list.")

        try:
            prev_value = self.data[key]
        except KeyError:
            if self._frozen:
                # Don't allow new keys to be added
                raise FrozenError("Cannot add new key.")
        else:
            if prev_value == value:
                return

            if self._frozen and not isinstance(value, type(prev_value)):
                raise FrozenError("Incompatible type.")

            try:
                self.children.remove(prev_value)
            except ValueError:
                pass

        self.data[key] = value
        self.modified = True

    def __eq__(self, other):
        if isinstance(other, WatchBase):
            return self.data == other.data
        else:
            return self.data == other

    def _process_value(self, value):
        if isinstance(value, (bool, int, float, str)):
            # Do nothing
            pass
        elif isinstance(value, WatchBase):
            # Do nothing
            pass
        elif isinstance(value, (dict, list, tuple)):
            value = self.from_data(value, parent=self)
        else:
            raise NotImplementedError

        return value

    @staticmethod
    def from_data(data, parent=None):
        if isinstance(data, dict):
            return WatchDict.with_parent(parent, **data)
        elif isinstance(data, (list, tuple)):
            return WatchList.with_parent(parent, *data)
        else:
            raise NotImplementedError

    def merge(self, other, strategy="ours"):
        if strategy not in self.MERGE_STRATEGIES:
            raise ValueError(f'Invalid merge strategy "{strategy}"')

    def to_data(self):
        """Recursively converts obj tree to vanilla python objects."""
        raise NotImplementedError

    def freeze_schema(self, dicts=True, lists=True, recursive=True):
        """Do not allow new elements to be added.

        Parameters
        ----------
        dicts: bool
            Do not allow new keys to be added to dictionaries.
            Replacement values must have the same data type.
        lists: bool
            Do not allow new elements to be appended to lists.
            Replacement values must have the same data type.
        recursive: bool
            Propagate freeze to children.
        """
        if isinstance(self, WatchDict):
            self._frozen = dicts
        elif isinstance(self, WatchList):
            self._frozen = lists
        else:
            raise NotImplementedError

        if recursive:
            for child in self.children:
                child.freeze_schema(
                    dicts=dicts,
                    lists=lists,
                    recursive=recursive,
                )


def _common_merge(key, existing_val, other_val, strategy):
    if isinstance(other_val, (dict, WatchDict)):
        if not isinstance(existing_val, WatchDict):
            raise ValueError(f'Existing value for index "{key}" is not expected dict.')
        existing_val.merge(other_val, strategy=strategy)
    elif isinstance(other_val, (list, WatchList)):
        if not isinstance(existing_val, WatchList):
            raise ValueError(f'Existing value for index "{key}" is not expected list.')
        existing_val.merge(other_val, strategy=strategy)


class WatchList(WatchBase):
    data: list

    def __init__(self, *init_list):
        super().__init__()
        self.data = [self._process_value(v) for v in init_list]

    def append(self, value):
        # Append None and overwrite so we can reuse __setitem__ logic
        if self._frozen:
            raise FrozenError("Cannot append.")
        self.data.append(None)
        self[-1] = value

    def extend(self, iterable):
        for value in iterable:
            self.append(value)

    def merge(self, other, strategy="ours"):
        """Merge existing entries with compatible other.

        *  `ours` - Favors own entries.
        """
        super().merge(other, strategy=strategy)

        if strategy == "ours":
            for i, other_val in enumerate(other):
                try:
                    existing = self[i]
                except IndexError:
                    self.append(other_val)
                    continue
                _common_merge(i, existing, other_val, strategy=strategy)
        elif strategy == "theirs":
            raise NotImplementedError
        else:
            raise NotImplementedError

    def to_data(self):
        return [v.to_data() if isinstance(v, WatchBase) else v for v in self]


class WatchDict(WatchBase):
    data: dict

    def __init__(self, **init_dict):
        super().__init__()
        self.data = {k: self._process_value(v) for k, v in init_dict.items()}

    def keys(self):
        return self.data.keys()

    def values(self):
        return self.data.values()

    def items(self):
        for item in self.data.items():
            yield item

    def update(self, d):
        """Overwrite (possibly) existing entries with contents of ``d``."""
        for k, v in d.items():
            self[k] = v

    def merge(self, other, strategy="ours"):
        """Recursively merge in ``default``, favoring ``self``."""
        super().merge(other, strategy=strategy)

        if strategy == "ours":
            for key, value in other.items():
                if key in self:
                    _common_merge(key, self[key], value, strategy=strategy)
                else:
                    self[key] = value
        elif strategy == "theirs":
            raise NotImplementedError
        else:
            raise NotImplementedError

    def to_data(self):
        return {
            k: v.to_data() if isinstance(v, WatchBase) else v for k, v in self.items()
        }


class ConfigStore(WatchDict):
    def __init__(self, filename="settings.json", autosave=True):
        """Create a ConfigStore.

        Parameters
        ----------
        filename: str
            File path to store persistent configs.
        autosave: bool
            Save after every attribute set.
            Can be temporarily disabled using contextmanager.
        """
        filename = str(filename)
        self.filename = filename

        try:
            with open(filename, "r") as f:
                data = json.load(f)
        except OSError:
            data = {}

        super().__init__(**data)

        if not filename.endswith(".json"):
            raise ValueError("filename must end in '.json'")

        self._autosave_enabled = autosave
        self._autosave_enabled_stack = []

    def __setitem__(self, key, value):
        if not isinstance(key, str):
            raise ValueError(f"Not allowed key datatype: {type(value)}")
        if not isinstance(value, (bool, int, float, str, tuple, list, dict, WatchBase)):
            raise ValueError(f"Not allowed value datatype: {type(value)}")

        super().__setitem__(key, value)

    def __enter__(self):
        """Disable autosaves within context manager; perform single save at end."""
        self._autosave_enabled_stack.append(self._autosave_enabled)
        self._autosave_enabled = False
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self._autosave_enabled = self._autosave_enabled_stack.pop()
        self.modified_cb()

    def modified_cb(self):
        """Only save if appropriate. Called frequently internally."""
        if not self.modified:
            return
        if not self._autosave_enabled:
            return
        self.save()

    def save(self):
        """Explicit write to disk.

        Atomic (or as atomic as you're going to get) file-write.
        """
        tmp_filename = self.filename + ".tmp"
        with open(tmp_filename, "w") as f:
            json.dump(self.to_data(), f)
        os.rename(tmp_filename, self.filename)
        self.modified = False

    def update(self, *args, **kwargs):
        with self:
            super().update(*args, **kwargs)

    def merge(self, *args, **kwargs):
        with self:
            super().merge(*args, **kwargs)
