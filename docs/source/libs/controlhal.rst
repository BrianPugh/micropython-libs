ControlHAL
==========
Control Hardware Abstraction Layer.

This library provides inheritable base classes that simplifies reading inputs (sensors) and controlling outputs (actuators).
The interfaces to these classes relies heavily on both inheritance and composition so that peripherals can be easily swapped and combined.
Sensor reads and actuator writes are self-caching and self-limiting, meaning they can be efficiently
in quick succession without worrying about physical implications.
This allows code to be very loosely coupled, for example:

.. code-block:: python

   # Conventional: need to pass around a cached value.
   while True:
       temperature = read_temperature()
       print(f"temperature: {temperature}°C")
       if temperature > 100:
           print("Boiling")
       sleep(0.5)

   # ControlHAL: read sensor as much as your want.
   # Rapid repeated reads will return a cached value.
   while True:
       print(f"temperature: {sensor()}°C")
       if sensor() > 100:
           print("Boiling")

See the source files for more details on function and class APIs.
Anytime that a ``machine.Pin`` is referenced, a ``machine.Signal``
or ``signal.Signal`` may be a more appropriate choice.

Dependencies
^^^^^^^^^^^^

No Dependencies

Optional
~~~~~~~~

* ``ringbuffer`` - Only used in the ``Derivative`` virtual sensor.

Protocol Summary
^^^^^^^^^^^^^^^^
The methods for each class in ControlHAL is summarizes in the table below:

+-------------------+-------------------------+------------------------------+----------------------------+--------------------------------------+
|                   | Sensor                  | Actuator                     | Controller                 | ControlLoop                          |
+===================+=========================+==============================+============================+======================================+
| ``__call__()``    | Read sensor (SI).       | Read setpoint (%).           | N/A                        | Predict actuator % from sensor (SI). |
+-------------------+-------------------------+------------------------------+----------------------------+--------------------------------------+
| ``__call__(val)`` | ``NotImplementedError`` | Write setpoint & device (%). | Predict actuator value (%) | Args/Kwargs are passed to            |
|                   |                         |                              | from sensor(s) value (SI). | ``controller.__call__``.             |
+-------------------+-------------------------+------------------------------+----------------------------+--------------------------------------+
| ``read()``        | Read sensor (SI).       | Read setpoint (%).           | Read setpoint (SI).        | Read sensor (SI).                    |
+-------------------+-------------------------+------------------------------+----------------------------+--------------------------------------+
| ``write(val)``    | ``NotImplementedError`` | Write setpoint (%) & device. | Write setpoint (SI).       | Write setpoint to controller (SI).   |
+-------------------+-------------------------+------------------------------+----------------------------+--------------------------------------+
| ``estop()``       | Prevents future reads.  | Writes ``0.0`` to setpoint   | No effect.                 | Propagate ``estop`` call to all      |
|                   | Subsequent reads return | & device. Disables future    |                            | attributes and controllers.          |
|                   | last cached value.      | writes.                      |                            |                                      |
+-------------------+-------------------------+------------------------------+----------------------------+--------------------------------------+
| get ``setpoint``  | Always returns 0.       | Get setpoint (%).            | Get setpoint (SI).         | Get controller's setpoint (SI).      |
+-------------------+-------------------------+------------------------------+----------------------------+--------------------------------------+
| set ``setpoint``  | ``NotImplementedError`` | Set setpoint (%).            | Set setpoint (SI).         | Set controller's setpoint (SI).      |
+-------------------+-------------------------+------------------------------+----------------------------+--------------------------------------+

In this table:

* SI_ - sane metric values appropriate for the sensor.

* % - A floating point value ranging from [0, 1] representing 0% ~ 100%.

All classes described inherit from the ``Peripheral`` base class.

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

Sensor can be oversampled_ by providing an integer value ``samples`` to ``__init__``.
Defaults to ``1`` sample per read (i.e. no oversampling).

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

Uses an internal virtual timer and intended for relatively slow processes like controlling a heater (period > 1 second).

.. code-block:: python

   from controlhal import TimeproportionalActuator

   heater = TimeProportionalActuator(Pin(1, Pin.OUT), period=10.0)
   heater.write(0.75)  # Heater will be on for 7.5 seconds, then off for 2.5 seconds.

PWMActuator
~~~~~~~~~~~
Varies an output actuator via pulse-width-modulation.

Similar to a ``TimeProportionalActuator``, but requires a supplied configured ``PWM`` object.
Intended for more rapid output devices, like LEDs or motors.

.. code-block:: python

   from controlhal import PWMActuator
   from machine import Pin, PWM

   pwm = PWM(Pin(12))
   pwm.freq(500)  # Set frequency to 500Hz
   actuator = PWMActuator(pwm)  # The PWMActuator class will handle setting duty-cycle

Multi
~~~~~
Collect a set of peripherals into a single class.
Can be used for more complex controllers while re-using other classes in this library.

.. code-block:: python

   from controlhal import Multi

   multi_sensor = Multi(sensor1, sensor2, sensor3)
   # Will read and return all 3 sensors
   sensor1_val, sensor2_val, sensor3_val = multi_sensor.read()

Multi can be subclassed to provide more structure/order to the constructor:

.. code-block:: python

   class MotorSensor(MultiSensor):
       def __init__(self, position, current, temperature):
           super().__init__(position, current, temperature)


Controller
^^^^^^^^^^
Abstract base class for predictive models that consume sensor data and produce actuator predictions.

At the very least, needs to implement the following methods:

.. code-block:: python

   class MyController(Controller):
       @property
       def parameters(self) -> Any:
           """Internal parameters that a controller can be constructed from.

           e.g. for a PID controller, this would be ``(k_p, k_i, k_d)``
           """

       def __call__(self, *args, **kwargs) -> float:
           """Given some sensor input, predict what the actuator value
           should be to drive the system to ``setpoint``.
           """

The controller setpoint can be written to either by directly writing to ``controller.setpoint`` or by calling the ``controller.write(val)`` method.

For a more indepth example, see the ``pid`` library for a PID controller.

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
.. _SI: https://en.wikipedia.org/wiki/International_System_of_Units
