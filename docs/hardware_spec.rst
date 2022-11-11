.. _hardware_spec:

Hardware Specifications
=======================
List of specifications in an attempt to keep consistency across this repository.

SPI
^^^

* Constructor's positional arguments will always be ``spi, cs``.

* If device has a relatively low baudrate, it will make
  a best-effort to lower the baudrate to it's operating
  clock, and restore the previous baudrate whenever
  communications are complete.

Units
^^^^^
Based on `CircuitPython's Design Guide`_, but favors human/scientific meaning over computational overhead. More units will be added as libraries are added.


+--------------+-------+-----------------------------+
| Property     | Type  | Unit                        |
+==============+=======+=============================+
| temperature  | float | degrees Celsius             |
| pressure     | float | hectopascal (hPA)           |
| weight       | float | grams (g)                   |
| flowrate     | float | cc/min                      |
| duty_cycle   | float | percentage in range [0, 1]  |
+--------------+-------+-----------------------------+


.. _CircuitPython's Design Guide: https://docs.circuitpython.org/en/7.2.x/docs/design_guide.html#sensor-properties-and-units
