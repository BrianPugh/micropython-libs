ControlHAL
==========
Control Hardware Abstraction Layer.
Classes to inherit from to simplify reading inputs (sensors) and controlling outputs (actuators).
The interfaces to these classes are designed so that peripherals can be swapped as easily as possible.
See the source files for more details on function and class APIs.

Dependencies
^^^^^^^^^^^^

No Dependencies

Sensor
^^^^^^
Abstract input sensor class.
Input devices should inherit from ``Sensor`` and implement the ``_raw_read`` method.
Optionally the ``_convert`` may also be implemented.
The default ``_convert`` method is an identity operation.

.. code-block:: python

    def _raw_read(self) -> float:
        """Read sensor.

        The returned value **may** be in standard units; or may be in a fast
        intermediate format for ``self._convert`` to post process into standard
        units. It is recommended to put fast, sensor reading logic into
        ``_raw_read``, and put expensive deferred logic into ``_convert``.
        This way, the sensor can be oversampled with minimal overhead.

        Returns
        -------
        float
        """


    def _convert(self, val: float) -> float:
        """Convert raw-value from ``_raw_read`` to a SI base unit float.

        Used to only call conversion once per oversample, rather than once per sample.

        Reference:
            https://en.wikipedia.org/wiki/SI_base_unit

        Parameters
        ----------
        val : float

        Returns
        -------
        float
        """

Sensor can be oversampled_ by specifying an integer value ``samples`` to ``__init__``.
Defaults to ``1`` sample per read.

ADCSensor
~~~~~~~~~
Sensor using an ADC input.

.. code-block:: python

   from controlhal import ADCSensor
   from machine import ADC

   sensor = ADCSensor(ADC(0))

Derivative
~~~~~~~~~~
A virtual sensor that acts as the time-derivative of another sensor.

.. code-block:: python

   from machine import ADC
   from controlhal import Derivative

   position_sensor = ADCSensor(ADC(0))
   velocity_sensor = Derivative(position_sensor)
   velocity = velocity_sensor.read()

Internally uses the `five-point stencil`_ to compute the derivative over a series of input measurements.
The returned derivative will be ``0`` until the internal buffer of length 5 fills up.

Actuator
^^^^^^^^
Abstract output actuator class.
Output devices should inherit from ``Actuator`` and implement the ``_raw_write`` method.

.. code-block:: python

   def _raw_write(self, val: float):
       """Perform actual write ``val`` to actuator.

       Parameters
       ----------
       val : float
           Value to write in range ``[0., 1.]``.
       """

Attempting to read from an actuator will return the current ``setpoint`` in range ``[0., 1.]``.
This value is also available via the read-only ``setpoint`` attribute.

TimeProportionalActuator
~~~~~~~~~~~~~~~~~~~~~~~~
Varies an output actuator via pulse-width-modulation.
Uses an internal virtual timer.

.. code-block:: python

   from controlhal import TimeproportionalActuator

   heater = TimeProportionalActuator(Pin(1, Pin.OUT), period=10.0)
   heater.write(0.75)  # Heater will be on for 7.5 seconds, then off for 2.5 seconds.

PWMActuator
~~~~~~~~~~~
Varies an output actuator via pulse-width-modulation.
Similar to a ``TimeProportionalActuator``, but requires a supplied configured ``PWM`` object.
Intended for more rapid output frequencies.

.. code-block:: python

   pass

Controller
^^^^^^^^^^
System that consumes sensor data and produces actuator predictions.

.. code-block:: python

   pass

ControlLoop
^^^^^^^^^^^
A self-contained control loop system for single-input/single-output systems.
For example, controlling a heating element based on feedback from a temperature sensor.
The example below uses the ``pid`` library.

.. code-block:: python

   from controlhal import ADCSensor, ControlLoop
   from machine import ADC, Pin
   from pid import PID
   from time import sleep

   temperature_sensor = ADCSensor(
       ADC(0), 100 / 65535
   )  # Hypothetical analog sensor [0, 100] °C
   heater = TimeProportionalActuator(Pin(1, Pin.OUT))
   pid = PID(0.05, 0.0001)

   control_loop = ControlLoop(heater, temperature_sensor, pid)

   while True:
       control_loop()  # Reads sensor, invokes controller, and updates actuator.
       sleep(0.25)


.. _five-point stencil: https://en.wikipedia.org/wiki/Five-point_stencil
.. _oversampled: https://en.wikipedia.org/wiki/Oversampling
