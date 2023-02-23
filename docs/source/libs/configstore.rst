ConfigStore
===========
Persistent key-value store with automatic write-to-disk and schema enforcement.

Dependencies
^^^^^^^^^^^^

No dependencies.

ConfigStore
^^^^^^^^^^^

In most cases, the resulting ``ConfigStore`` object can just be treated exactly like a dictionary.

.. code-block:: python

    from configstore import ConfigStore

    config = ConfigStore("settings.json")  # Will read/write to "settings.json"
    config["foo1"] = "bar1"  # Simple key/value store. Write is automatically performed.
    config["list_example"] = [1, 2, 3]  # lists work
    config["nested"] = {"foo2": "bar2"}  # So do nested dictionaries.

    config_reload = ConfigStore.load("settings.json")  # Load an existing config
    assert config_reload == config  # They should be the same.

    with config:  # defer writes until the contextmanager exits.
        config["a"] = 1
        config["b"] = 2
        config["c"] = 3


Supplying Dictionary Defaults
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Like a dictionary, the ``config`` object has an ``update`` method to merge in a dictionary.
The ``update`` method will overwrite existing keys:

.. code-block:: python

   config["foo"] = "bar"
   config["value"] = 123
   config.update({"name": "alice", "value": 456})

   assert config["foo"] == "bar"
   assert config["value"] == 456
   assert config["name"] == "alice"

To supply default values, use the ``merge`` method.
Existing values will not be overwritten.

.. code-block:: python

   config["foo"] = "bar"
   config["value"] = 123
   config.merge({"name": "alice", "value": 456})

   assert config["foo"] == "bar"
   assert config["value"] == 123
   assert config["name"] == "alice"


Freezing Schema
~~~~~~~~~~~~~~~
Often, once configured, the json schema should be fixed to prevent accidental misconfigurations.
This includes things like typoing keys, or assigning incorrect value datatypes.
Call the ``freeze_schema`` to freeze the ``ConfigStore`` object.

.. code-block:: python

   config["foo"] = "bar"
   config["my_list"] = [1, 2, 3]
   config.freeze_schema()

For dictionaries, attempting to assign a different datatype to a key will result in a ``FrozenError`` exception.

.. code-block:: python

   config["foo"] = 123  # raises FrozenError

For lists, values can no longer be appended to (list will have fixed length).
When replacing an element, the new element must have the same datatype.

.. code-block:: python

   config["my_list"].append(4)  # raises FrozenError
   config["my_list"][0] = "foo"  # raises FrozenError
   config["my_list"][1] = 42  # this is OK

Freezing only specific children types is possible:

.. code-block:: python

    config.freeze_schema(dicts=True, lists=True, recursive=True)  # Default values
