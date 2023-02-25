Installation
============

These libraries are intended for a micropython target.
We suggest using the `Belay Package Manager`_

Install Belay:

.. code-block:: bash

   pip install belay

Then, in your project's ``pyproject.toml``, add a section like:

.. code-block:: toml

   [tool.belay.dependencies]
   interp1d = "https://github.com/BrianPugh/micropython-libs/blob/main/lib/interp1d.py"

Next, run ``belay update`` to pull down the latest changes.

Finally, to transfer the libraries to your device:

.. code-block:: bash

   belay install <PORT>

While developing, it can be useful then to also run a file after innstalling your project:

.. code-block:: bash

   belay install <PORT> --run my_script.py


.. _Belay Package Manager: https://belay.readthedocs.io/en/latest/Package%20Manager.html
