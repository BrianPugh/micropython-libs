from time import ticks_add, ticks_diff, ticks_ms

import micropython
from machine import Pin, Timer


class DebouncedPin:
    def __init__(self, pin, callback, debounce_period_ms=20, timer_id=-1):
        """Invoke callback on rising and falling edge.

        Parameters
        ----------
        pin: machine.Pin
        callback: callable
            Function called when ``trigger`` happens.
            Takes a single argument; the current
        """
        self.pin = pin
        self._prev_val = pin()
        pin.irq(handler=self._pin_trigger_handler)

        self.callback = callback
        self.debounce_period_ms = debounce_period_ms

        self.timer = Timer(timer_id)
        self._timer_running = False
        self._timer_callback_ref = self._timer_callback  # Alloc happens here

    def _pin_trigger_handler(self, pin):
        if self._timer_running:
            return

        val = pin()
        if val != self._prev_val:
            self._prev_val = val
            self._timer_running = True
            self.timer.init(
                period=self.debounce_period_ms,
                callback=self._timer_callback_ref,
                mode=Timer.ONE_SHOT,
            )

    def _timer_callback(self, timer):
        self._timer_running = False

        val = self.pin()
        if val == self._prev_val:
            if self.callback:
                micropython.schedule(self.callback, val)
        self._prev_val = val

    # TODO: mimic Pin interface
