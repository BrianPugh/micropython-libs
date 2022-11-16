"""RobotDyn triac-based AC Dimmer Control.

When pulse skipping, full cycles are skipped.
"""
from time import ticks_diff, ticks_us

import micropython
from controlhal import Actuator
from machine import Pin, Timer


class RobotDyn(Actuator):
    def __init__(self, zc, control, period=None, timer_id=-1):
        """

        Parameter
        ---------
        zc: machine.Pin
            Zero cross input pin.
        psm: machine.Pin
            PSM output pin.
        """
        super().__init__(period=period)

        zc.init(Pin.IN)
        control.init(Pin.OUT)

        self.zc = zc
        self.control = control
        self._timer = Timer(timer_id)
        self._setpoint_delay_ms = 0
        zc.irq(trigger=Pin.IRQ_RISING, handler=self._zc_handler)

        # for autodetecting mains frequency.
        self._zc_count = 0
        self._zc_t0 = 0
        self._zc_period_us = 0

    def _zc_handler(self, pin):
        # PERIOD AUTODETECTION
        if self._zc_count == 0:
            self._zc_t0 = ticks_us()
        if self._zc_count < 9:  # 8 half cycles
            self._zc_count += 1
            return
        elif not self._zc_period_us:
            # Fast integer divide-by-8 (2^3)
            self._zc_period_us = ticks_diff(ticks_us(), self._zc_period_us) >> 3

        if self._setpoint_delay_ms:
            self._timer.init(
                mode=Timer.ONE_SHOT,
                period=self._setpoint_delay_ms,
                callback=self._timer_callback,
            )
        else:
            self._timer_callback(self._timer)

    def _timer_callback(self, timer):
        self.control.on()
        # todo; delay maybe like 10uS?
        self.control.off()

    def _raw_write(self, val):
        self._setpoint_delay_ms = round(val * 0.97 * self._zc_period_us / 1000)
