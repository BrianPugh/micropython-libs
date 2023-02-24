PIDAutotune
===========
Proportional-Integral-Derivative autotuning using the Relay Method.

Dependencies
^^^^^^^^^^^^

* ``controlhal``
* ``ringbuffer``

While not a direct dependency, this library is intended to be used in conjunction with the ``pid`` library.

PIDAutotune
^^^^^^^^^^^
The main class, ``PIDAutotune``, is itself a ``controlhal.Controller``.
For typical usage, you can temporarily swap out

.. code-block:: python

   from controlhal import ControlLoop, AutotuneSuccess, AutotuneFailure
   from pid import PID
   from pidautotune import PIDAutotune
   from time import sleep

   heater = get_actuator()  # Just some controhal.Actuator
   thermometer = get_sensor()  # Just some controlhal.Sensor

   pid = PID(0.05, 0.001)
   control_loop = ControlLoop(heater, thermometer, pid)

   # Set the hysterisis to be a small value, but larger than random peak-to-peak
   # sensor noise.
   autotuner = PIDAutotune(control_loop.setpoint, hysterisis=1.5)

   # Could do normal control_loop things, but here we will temporarily
   # swap out the PID controller for the PIDAutotune controller.

   with control_loop.use(autotuner):
       try:
           while True:
               control_loop()
               sleep(0.5)
       except AutotuneSuccess as e:
           print(f"PID parameters: {e.parameters}")
           pid.parameters = e.parameters
       except AutotuneFailure:
           print("Autotuner failed to converge")

   # Continues on with ``pid``

By default, parameters are computed using the ``"some-overshoot"`` method. Available tuning formulas include:

* ``"some-overshoot"`` - Default

* ``"ziegler-nichols-p"``

* ``"ziegler-nichols-pi"``

* ``"ziegler-nichols-pid"``

* ``"no-overshoot"``

* ``"tyreus-luyben"``

The parameter computation technique can be specified by setting ``method`` when creating the autotuner.
Alternatively, a tuning rule can be specified

.. code-block:: python

   autotuner = PIDAutotune(80.0, hysterisis=1.5, method="ziegler-nichols-pi")
   # after running until AutotuneSuccess:
   k_p, k_i, k_d = autotuner.compute_tunings("ziegler-nichols-pid")

Acknowledgements
^^^^^^^^^^^^^^^^
This library is heavily modified from `hirschmann's`_ implementation.
In turn, his library was inspired by Brett Beauregard's arduino library, `PIDAutotuneLibrary`_.
Large portions of the code have been rewritten to favor readability (like using floating point) over microcontroller performance.

.. _hirschmann's: https://github.com/hirschmann/pid-autotune/blob/master/autotune.py
.. _PIDAutotuneLibrary: https://github.com/br3ttb/Arduino-PID-AutoTune-Library
