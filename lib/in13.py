"""Driver for I2C in-13 nixie tube.

https://www.tindie.com/products/eclipsevl/in-13-bargraph-nixie-tube-with-driver-and-dc-dc/?pt=ac_prod_search
"""


class IN13:
    def __init__(self, i2c, addr=0x14):
        """Create an IN13 indicator object.

        Parameters
        ----------
        i2c: machine.I2C
            Pre-configured i2c object.
        addr: int
            Address of indicator. Configured by in13 driver A0 pin.
            If A0 is connected to GND, the address is 0x13.
            If A0 is connected to +5V, the address is 0x14.
        """
        self.i2c = i2c
        self.addr = addr
        self._value = 0
        self._filter = 0

        # Set control mode to digital
        self.i2c.writeto_mem(addr, 0, bytes([0x01]))

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        """Set indicator between 0.0 (off) and 1.0 (fully on)."""
        if not (0 <= value <= 1):
            raise ValueError
        self._value = value
        value = round(0xFF * value)
        self.i2c.writeto_mem(self.addr, 0x01, bytes([value]))

    @property
    def filter(self):
        return self._filter

    @filter.setter
    def filter(self, value):
        """Adjust low-pass filter between 0.0 (fast) and 1.0 (slow)."""
        if not (0 <= value <= 1):
            raise ValueError
        self._filter = value
        value = round(0x1F * value)
        self.i2c.writeto_mem(self.addr, 0x02, bytes([value]))
