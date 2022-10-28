"""Debounced input pin for reading buttons/switches.

Typical use-case 1; ``handler`` will be invoked whenever
a debounced press is detected. This assumes button connects
to ground.

.. code-block:: python

    from debouncedpin import DebouncedPin

    count = 0


    def handler(pin):
        nonlocal count
        count += 1
        print(count)


    pin = DebouncedPin(pin, Pin.PULL_UP)
    pin.irq(handler, DebouncedPin.IRQ_FALLING)

    while True:
        time.sleep(1)


Alternatively, normal reads via ``value`` or ``__call__``
return the debounced value and are safe to be used in a
program main loop:

.. code-block:: python

    from debouncedpin import DebouncedPin

    count = 0
    pin = DebouncedPin(pin, Pin.PULL_UP)
    while True:
        if not pin.value():
            print("Button is pressed")
        time.sleep(1)
"""
import micropython
from machine import Pin, Timer


class DebouncedPin(Pin):
    def __init__(self, id, pull=-1, *, period=15, timer_id=-1):
        """Debounced input pin for reading buttons/switches.

        Unlike ``Pin``, doesn't take in ``mode`` since it must
        be ``Pin.IN``.

        Parameters
        ----------
        id: Any
            Valid value types are:
                * ``int`` (an internal Pin identifier)
                * ``str`` (a Pin name)
                * ``tuple`` (pair of [port, pin]).
        period: int
            Debounce time in milliseconds required for consistent pin
            state to be considered updated value.
            Defaults to 15 milliseconds.
        """
        super().__init__(id, Pin.IN, pull)
        super().irq(handler=self._pin_trigger_handler)

        self._val = self._prev_val = super().value()
        self.period = period

        self._user_handler = None
        self._user_trigger = Pin.IRQ_RISING | Pin.IRQ_FALLING

        self.timer = Timer(timer_id)
        self._timer_running = False
        self._timer_callback_ref = self._timer_callback  # Alloc happens here

    def value(self):
        """Read debounced pin value.

        Will inherently be delayed to actual value by ``period`` ms.
        """
        return self._val

    def __call__(self):
        """Equivalent to ``DebouncedPin.value()``."""
        return self.value()

    def irq(self, handler=None, trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING):
        """Invoke callback on rising and falling edge (debounced).

        No internal limitations on handler; invoked via ``micropython.schedule``.

        Parameters
        ----------
        handler: callable
            Function called when ``trigger`` happens (debounced).
            The handler must take exactly one argument which is the ``DebouncedPin`` instance.
        trigger:
            event which can trigger ``handler``.
            Possible values are:
                * ``Pin.IRQ_FALLING`` interrupt on falling edge.
                * ``Pin.IRQ_RISING`` interrupt on rising edge.
        """
        self._user_handler = handler
        self._user_trigger = trigger

    def _pin_trigger_handler(self, pin):
        """When pin changes state, triggers a timer to execute ``_timer_callback`` in ``period`` milliseconds."""
        if self._timer_running:
            return

        val = pin()
        if val != self._prev_val:
            self._prev_val = val
            self._timer_running = True
            self.timer.init(
                period=self.period,
                callback=self._timer_callback_ref,
                mode=Timer.ONE_SHOT,
            )

    def _timer_callback(self, timer):
        """Check if pin is in same state as when timer was triggered. If so, updates the stable pin state and schedules the user callback."""
        self._timer_running = False

        val = super().value()
        consistent_read = val == self._prev_val
        self._prev_val = val
        if consistent_read:
            self._val = val
            if self._user_handler:
                if (val and self._user_trigger & Pin.IRQ_RISING) or (
                    not val and self._user_trigger & Pin.IRQ_FALLING
                ):
                    micropython.schedule(self._user_handler, self)
