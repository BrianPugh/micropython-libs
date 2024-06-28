import pytest
from configstore import ConfigStore, FrozenError, WatchDict, WatchList


def test_watch_dict_init_default():
    wd = WatchDict()
    assert wd.modified is False


def test_watch_dict_init_dict():
    wd = WatchDict(foo="bar", bloop="bleep")
    assert wd.modified is False
    assert wd["foo"] == "bar"
    assert wd["bloop"] == "bleep"
    assert list(wd.keys()) == ["foo", "bloop"]
    assert list(wd.values()) == ["bar", "bleep"]


def test_watch_dict_insert_str():
    wd = WatchDict()
    assert wd.modified is False

    wd["foo"] = "bar"

    assert wd.modified is True
    assert wd["foo"] == "bar"

    wd.modified = False
    assert wd.modified is False


def test_watch_dict_insert_nested():
    wd = WatchDict()
    assert wd.modified is False

    wd["foo"] = {}

    assert wd.modified is True
    assert isinstance(wd["foo"], WatchDict)
    assert wd["foo"].modified is False

    wd.modified = False
    assert wd.modified is False

    wd["foo"]["bar"] = "baz"
    assert wd["foo"].modified is True
    assert wd.modified is True

    wd.modified = False
    assert wd.modified is False
    assert wd["foo"].modified is False

    wd["watchlist"] = WatchList()
    wd["watchlist"].append(2)
    assert wd["watchlist"] == [2]

    wd["watchdict"] = WatchDict()
    wd["watchdict"]["key"] = "value"
    assert wd["watchdict"]["key"] == "value"


def test_watch_list_init_default():
    wd = WatchList()
    assert wd.modified is False


def test_watch_list_init_list():
    wd = WatchList("foo", "bar")
    assert wd.modified is False
    assert wd == ["foo", "bar"]


def test_watch_list_append():
    wd = WatchList()
    assert wd.modified is False

    wd.append("foo")
    wd.append("bar")
    assert wd.modified is True
    assert wd == ["foo", "bar"]


def test_watch_list_extend():
    wd = WatchList()
    assert wd.modified is False

    wd.extend(["foo", "bar"])
    assert wd.modified is True
    assert wd == ["foo", "bar"]


def test_watch_list_append_nested():
    wd = WatchList()
    assert wd.modified is False

    wd.append([])
    assert wd.modified is True
    wd.modified = False

    wd[0].append("foo")
    assert wd == [["foo"]]
    assert wd.modified is True
    assert wd[0].modified is True

    wd.modified = False

    assert wd.modified is False
    assert wd[0].modified is False


def test_watch_dict_list_nested():
    wd = WatchDict()
    wd["foo"] = []

    wd.modified = False

    wd["foo"].append("bar")
    assert wd.modified is True
    assert wd["foo"].modified is True

    wd.modified = False

    assert wd.modified is False
    assert wd["foo"].modified is False

    assert len(wd.children) == 1
    wd["foo"] = 5
    assert len(wd.children) == 0

    assert wd.modified is True


def test_watch_dict_update():
    wd = WatchDict()
    assert wd.modified is False

    wd["foo"] = 3
    assert wd.modified is True
    wd.modified = False

    update_d = {"foo": {"bar": "baz"}}
    wd.update(update_d)
    assert wd.modified is True
    assert wd == update_d

    wd.modified = False

    wd["foo"]["bar"] = 5
    assert wd.modified is True


def test_watch_dict_merge():
    wd = WatchDict()
    assert wd.modified is False
    wd["foo1"] = {"bar1": {"baz1": "bop1"}}
    wd.merge(
        {
            "foo1": {
                "bar1": {
                    "baz1": "BOP1",
                    "baz2": "BOP2",
                },
            },
            "bar2": 5,
        }
    )
    assert wd == {
        "foo1": {
            "bar1": {
                "baz1": "bop1",
                "baz2": "BOP2",
            },
        },
        "bar2": 5,
    }


def test_watch_list_merge():
    wl = WatchList()
    wl.append([1, 2, 3])
    wl.append([4, 5, 6])
    other = [["a", "b", "c", "d"], ["e", "f", "g", "h"], "i"]
    wl.merge(other)
    assert wl == [[1, 2, 3, "d"], [4, 5, 6, "h"], "i"]


def test_invalid_merge_strategy():
    wl = WatchList()
    with pytest.raises(ValueError):
        wl.merge([], strategy="foo")


def test_incompatible_merge_dict():
    wd = WatchDict()
    assert wd.modified is False
    wd["foo1"] = {"bar1": {"baz1": "bop1"}}
    with pytest.raises(TypeError):
        wd.merge({"foo1": 5})


def test_incompatible_merge_list():
    wl = WatchList([1, 2, ["a", "b"]])
    with pytest.raises(TypeError):
        wl.merge([4, 5, 6])


def test_init(tmp_path):
    config = ConfigStore(tmp_path / "config.json", autosave=False)
    assert config.modified is False

    config["foo"] = {}
    assert config.modified is True


def test_autosave(tmp_path, mocker):
    config_fn = tmp_path / "config.json"
    config = ConfigStore(config_fn)
    spy_save = mocker.spy(config, "save")

    config["foo"] = {}
    assert len(spy_save.call_args_list) == 1
    assert config.modified is False

    config["bar"] = 1
    assert len(spy_save.call_args_list) == 2
    assert config.modified is False

    config["foo"]["bar"] = 2
    assert len(spy_save.call_args_list) == 3
    assert config.modified is False

    config["foo"]["bar"] = 3
    assert len(spy_save.call_args_list) == 4
    assert config.modified is False

    # Assigning same value to key should NOT trigger a save.
    config["foo"]["bar"] = 3
    assert len(spy_save.call_args_list) == 4
    assert config.modified is False

    config_reload = ConfigStore(config_fn)
    assert config_reload == config


def test_contextmanager(tmp_path, mocker):
    config_fn = tmp_path / "config.json"
    config = ConfigStore(config_fn)
    spy_save = mocker.spy(config, "save")

    with config:
        config["foo"] = {}
        config["bar"] = 1
        config["foo"]["bar"] = 2

    spy_save.assert_called_once()

    config_reload = ConfigStore(config_fn)
    assert config_reload == config


def test_bool(tmp_path):
    config_fn = tmp_path / "config.json"
    config = ConfigStore(config_fn)

    assert bool(config) is False

    config["bar"] = 1

    assert bool(config) is True


def test_update():
    wd = WatchDict()

    expected = {
        "default_profile": 1,
        "profiles": [
            {
                "name": "Normal",
                "temperature": 100,
            },
            {
                "name": "Bold",
                "temperature": 110,
            },
        ],
    }

    wd.update(expected)
    assert wd == expected
    assert isinstance(wd["profiles"], WatchList)
    assert isinstance(wd["profiles"][0], WatchDict)
    assert len(wd["profiles"].children) == 2


def test_merge(tmp_path, mocker):
    config_fn = tmp_path / "config.json"
    config = ConfigStore(config_fn)
    spy_save = mocker.spy(config, "save")

    config.update(
        {
            "default_profile": 1,
            "profiles": [
                {
                    "name": "Normal",
                    "temperature": 100,
                },
                {
                    "name": "Bold",
                    "temperature": 110,
                },
            ],
        }
    )
    assert len(spy_save.call_args_list) == 1

    # This would classically be the default configuration.
    # The default configuration may have new keys that are
    # not in the user's config.
    config.merge(
        {
            "name": "EspressOS",
            "default_profile": 0,
            "profiles": [
                {
                    "name": "unnamed",
                    "temperature": 90,
                    "duration": 30,
                },
                {
                    "name": "unnamed",
                    "temperature": 91,
                    "duration": 31,
                },
            ],
        }
    )
    assert len(spy_save.call_args_list) == 2

    assert config == {
        "name": "EspressOS",
        "default_profile": 1,
        "profiles": [
            {
                "name": "Normal",
                "temperature": 100,
                "duration": 30,
            },
            {
                "name": "Bold",
                "temperature": 110,
                "duration": 31,
            },
        ],
    }


def test_freeze_schema(mocker, tmp_path):
    config_fn = tmp_path / "config.json"
    config = ConfigStore(config_fn)

    config.update(
        {
            "default_profile": 1,
            "profiles": [
                {
                    "name": "Normal",
                    "temperature": 100,
                },
                {
                    "name": "Bold",
                    "temperature": 110,
                },
            ],
        }
    )
    assert isinstance(config["profiles"], WatchList)
    assert isinstance(config["profiles"][0], WatchDict)

    config["default_profile"] = 2
    config.freeze_schema()
    assert config.frozen is True

    config["default_profile"] = 3  # OK: existing key, same dtype

    with pytest.raises(FrozenError):
        config["profiles"][0] = {}  # Cannot overwrite dict

    with pytest.raises(FrozenError):
        config["profiles"] = []  # Cannot overwrite list

    with pytest.raises(FrozenError):
        config["new-key"] = 3  # BAD: new-key

    with pytest.raises(FrozenError):
        config["default_profile"] = "foo"  # BAD: different dtype

    with pytest.raises(FrozenError):
        # Testing recursion propagated
        config["profiles"][0]["new-key"] = 3  # BAD: new-key

    with pytest.raises(FrozenError):
        config["profiles"].append(3)  # BAD: append


def test_freeze_schema_non_recursive(mocker, tmp_path):
    config_fn = tmp_path / "config.json"
    config = ConfigStore(config_fn)

    config.update(
        {
            "default_profile": 1,
            "profiles": [
                {
                    "name": "Normal",
                    "temperature": 100,
                },
                {
                    "name": "Bold",
                    "temperature": 110,
                },
            ],
        }
    )
    assert isinstance(config["profiles"], WatchList)
    assert isinstance(config["profiles"][0], WatchDict)

    config["default_profile"] = 2
    config.freeze_schema(recursive=False)
    assert config.frozen is True

    assert config["profiles"][0].frozen is False


def test_config_store_incompatible_value_type(tmp_path):
    config_fn = tmp_path / "config.json"
    config = ConfigStore(config_fn)
    with pytest.raises(TypeError):
        config["foo"] = b"bytes"


def test_config_store_incompatible_key_type(tmp_path):
    config_fn = tmp_path / "config.json"
    config = ConfigStore(config_fn)
    with pytest.raises(TypeError):
        config[5] = b"bytes"


def test_config_store_incompatible_file_extension(tmp_path):
    config_fn = tmp_path / "config.txt"
    with pytest.raises(ValueError):
        ConfigStore(config_fn)
