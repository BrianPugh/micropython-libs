PID
===
Proportional-Integral-Derivative Controller.

A PID controller predicts how much an actuator should be given a relevant feedback signal.
A common example is in a water boiler where the PID controller predicts how much the heating element should be turned on given a feedback temeperature signal from a temperature sensor.

Dependencies
^^^^^^^^^^^^

* ``controlhal``

PID
^^^
For most use-cases, the ``PID`` class takes in up to 3 inputs:

.. code-block:: python

   from pid import PID

   controller = PID(0.05)  # A "P" controller
   controller = PID(0.05, 0.001)  # A "PI" controller
   controller = PID(0.05, 0.001, 3.2)  # A "PID" controller

By default, the output is limited to the floating-point range ``[0, 1]``, which should be interpreted as 0 to 100%.
This output normalization makes it easier to hook up different actuators to a PID controller.

.. code-block:: python

   controller = PID(0.5, setpoint=80.0)  # Setpoint can be configured at initialization.
   controller.setpoint = 80  # Can directly set the attribute whenever.

The PID controller should be called at a fix interval. If called faster than the specified ``period`` (defaults to 0.01 seconds), then the internal state will **not** be updated, and the previous actuator prediction value will be returned.

.. code-block:: python

   while True:  # Main application loop
       temperature = sensor.read()
       actuator_power = controller(temperature)
       actuator.write(actuator_power)

This sensor-read, actuator-write code is wrapped up in ``controlhal.ControlLoop``.

Acknowledgements
^^^^^^^^^^^^^^^^
This library is modified from `m-lundberg's`_ implementation.
In turn, his library was inspired by Brett Beauregard's arduino library, `PIDLibrary`_.

I added the following modifications:

1. Fix some micropython incompatibilities.

2. Don't accumulate the integral component while the acutator is in saturation. This helps prevent `integral windup`_.

3. Change a few parameter names to be consistent with some other libraries.

4. Set default output limits to ``(0, 1)``. The ``error_map`` feature has been removed in favor of a normalized output.


.. _m-lundberg's: https://github.com/m-lundberg/simple-pid
.. _PIDLibrary: https://github.com/br3ttb/Arduino-PID-Library
.. _integral windup: https://en.wikipedia.org/wiki/Integral_windup
