"""MAX6675 interface.

Typical use:

.. code-block::  python

    from machine import SPI
    from max6675 import Max6675
    from time import sleep

    spi = SPI()
    temperature_sensor = Max6675(spi)

    while True:
        temperature_celsius = temperature_sensor()
        print(f"Temperature: {temperature_celsius}°C.")
        sleep(0.22)
"""
import re
import time

try:
    import micropython  # pyright: ignore[reportMissingImports]
except ModuleNotFoundError:
    micropython = None

if micropython:
    time_ms = time.ticks_ms  # pyright: ignore[reportGeneralTypeIssues]
    ticks_diff = time.ticks_diff  # pyright: ignore[reportGeneralTypeIssues]
    const = micropython.const
else:  # pragma: no cover
    time_ms = lambda: int(round(time.monotonic_ns() / 1_000_000))  # noqa: E731
    ticks_diff = lambda x, y: x - y  # noqa: E731
    const = lambda x: x  # noqa: E731

_baudrate_pattern = re.compile(r"baudrate=(\d+)")


class OpenThermocouple(Exception):
    """Thermocouple input is open."""


def _interpret_buf(data):
    """Interpret signal from Max6675.

    Parameters
    ----------
    data: bytearray
        Read in data (2 bytes).

    Returns
    -------
    float
        Temperature in celsius.
    """
    dummy = data[0] >> 7
    if dummy != 0:
        raise Exception("Expected dummy bit to be 0.")
    tc_open = (data[1] >> 2) & 0b0000_0001
    if tc_open:
        raise OpenThermocouple
    signal = ((data[0] & 0b0111_1111) << 5) | ((data[1] & 0b1111_1000) >> 3)
    celsius = signal / 4
    return celsius


def _prev_baudrate(spi):
    res = _baudrate_pattern.search(repr(spi))
    if res is None:
        raise Exception("Invalid SPI repr.")
    return int(res.group(1))


class Max6675:
    """The MAX6675 is a thermocouple-to-digital converter with a built-in 12-bit ADC.

    The MAX6675 contains cold-junction compensation sensing and correction,
    a digital controller, an SPI-compatible interface, and associated control logic.
    """

    CONVERSION_TIME_MS = 220  # Max Conversion Time

    def __init__(self, spi, cs, spi_preread_callback=None, baudrate=4_000_000):
        """Create a Max6675 object.

        Parameters
        ----------
        spi: machine.SPI
            SPI interface
        cs: machine.Pin
            Chip select.
            Must be configured as ``Pin.OUT``.
        spi_preread_callback: Optional[None, callable]
            Optional function to call before taking over the SPI bus.
        baudrate: int
            The MAX6675 has a max frequency of 4.3MHz.
        """
        self.spi = spi
        self.cs = cs
        self.spi_preread_callback = spi_preread_callback
        self.baudrate = baudrate

        self._buf = bytearray(2)
        self._prev_val = None

        self._start_new_conversion()

        raise NotImplementedError

    def __call__(self):
        """Read from sensor."""
        return self.read()

    def _start_new_conversion(self):
        self.cs.on()
        self._prev_conversion_time = time_ms()

    def read(self):
        """Read from sensor.

        Returns
        -------
        float
            Temperature in celsius. Range [0, 1023.75] in 0.25 increments.
        """
        if ticks_diff(time_ms(), self._prev_conversion_time) < self.CONVERSION_TIME_MS:
            return self._prev_val
        if self.spi_preread_callback:
            self.spi_preread_callback()
        prev_baudrate = _prev_baudrate(self.spi)
        self.spi.init(baudrate=self.baudrate)
        self.cs.off()  # Force CS low to output the first bit on the MAX6675 SO pin.
        self.spi.readinto(self._buf)
        self._prev_val = _interpret_buf(self._buf)
        self._start_new_conversion()
        self.spi.init(baudrate=prev_baudrate)  # Restore baudrate
        return self._prev_val
