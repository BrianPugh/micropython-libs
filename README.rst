|Python compat| |PyPi| |GHA tests| |Codecov report|

.. inclusion-marker-do-not-remove

micropython-libs
================

This repository contains a collection of single-file libraries intended for
a micropython target.

Generic Libraries
=================
These libraries generally don't depend on specific hardware and primarily contain just
software algorithms/abstractions.

* ``configstore`` - Persistent auto-write key-value store.

* ``controlhal`` - Abstractions for controlling a dynamic system. Easy PID control loops.

* ``debouncedpin`` - Debounced ``Pin`` drop-in that automatically handles switch debouncing.
  Can also simultaneously drive an LED using the same pin with ``DebouncedLedPin``.

* ``interp1d`` - One dimensional interpolation functions.

* ``oversample`` - Oversample a sensor to improve the SNR and measurement resolution
  at the cost of increased CPU utilization and reduced throughput.

* ``pid`` - PID controller. Not recommended for fast processes (not for quadcopters). Recommended interface: ``controlhal``.

* ``pidautotune`` - Autotune for PID controllers. Recommended interface: ``controlhal``.

* ``ringbuffer`` - RingBuffer with builtin statistical methods.

Hardware Drivers
================
These libraries contain drivers for specific hardware.
Whenever possible, these drivers abide by the standards in `docs/hardware`_.

* ``max6675`` - MAX6675 Cold-Junction-Compensated K-Thermocouple-to-Digital Converter (0°C to +1024°C).

Installation
============
We recommend using the `Belay Package Manager`_ for installing desired libraries.
To install Belay on your computer, run:

.. code-block:: bash

   pip install belay

Then, define your project name and dependencies in your project's ``pyproject.toml`` file. Belay assumes you have a python package in your project with the same name as ``tool.belay.name``:

.. code-block:: toml

   [tool.belay]
   name = "my_project_name"

   [tool.belay.dependencies]
   ringbuffer = "https://github.com/BrianPugh/micropython-libs/blob/main/lib/ringbuffer.py"

   [tool.pytest.ini_options]
   pythonpath = ".belay-lib"

Then, to actually download the dependencies (and update them if already downloaded), run the following in your project's root directory:

.. code-block:: bash

   belay update

Finally, to actually get the code onto your device, run:

.. code-block:: bash

   belay install [DEVICE-PORT]

You can specify other argument to ``belay install``, including cross-compiling the python code.

Repo Folder Structure
=====================

* ``lib/`` - Micropython modules.

*  ``tests/`` - Tests for micropython modules

*  ``demos/`` - For code that primarily interacts with hardware, these serve as minimal scripts for demonstrating their use.


.. _Belay Package Manager: https://belay.readthedocs.io/en/latest/Package%20Manager.html
.. |GHA tests| image:: https://github.com/BrianPugh/micropython-libs/workflows/tests/badge.svg
   :target: https://github.com/BrianPugh/micropython-libs/actions?query=workflow%3Atests
   :alt: GHA Status
.. |Codecov report| image:: https://codecov.io/github/BrianPugh/micropython-libs/coverage.svg?branch=main
   :target: https://codecov.io/github/BrianPugh/micropython-libs?branch=main
   :alt: Coverage
.. |Python compat| image:: https://img.shields.io/badge/>=python-3.8-blue.svg
.. |PyPi| image:: https://img.shields.io/pypi/v/libs.svg
        :target: https://pypi.python.org/pypi/libs
.. _docs/hardware: docs/hardware_spec.rst
