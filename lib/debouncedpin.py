"""Debounced input pin for reading buttons/switches.

Can also drive an LED using the same pin.

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
    def __init__(self, id, pull=-1, *, value=None, period=20, timer_id=-1):
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
        super().__init__(id, Pin.IN)
        self.init(pull=pull, value=value)

        self._last_val = super().value()  # last input read
        self._val = self._last_val  # Current steady-state input
        self.period = period

        self._user_handler = None
        self._user_trigger = Pin.IRQ_RISING | Pin.IRQ_FALLING

        self.timer = Timer(timer_id)
        self.timer.init(period=self.period, callback=self._timer_callback)

    def value(self, x=None):
        """Read debounced pin value.

        Will inherently be delayed to actual value by ``period`` ms.
        """
        if x is None:
            return self._val
        else:
            raise ValueError

    def __call__(self, x=None):
        """Equivalent to ``DebouncedPin.value()``."""
        return self.value(x=x)

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

    def _timer_callback(self, timer):
        """Check if pin is in same state as when timer was triggered. If so, updates the stable pin state and schedules the user callback."""
        val = super().value()
        consistent_read = val == self._last_val
        self._last_val = val
        if consistent_read and val != self._val:
            self._val = val
            if self._user_handler:
                if (val and self._user_trigger & Pin.IRQ_RISING) or (
                    not val and self._user_trigger & Pin.IRQ_FALLING
                ):
                    micropython.schedule(self._user_handler, self)

    def pressed(self):
        """Return button state.

        If ``PULL_UP``, it assumes button pulls down.
        If ``PULL_DOWN`` or not set, it assumes button pulls up.

        Returns
        -------
        bool
            ``True`` if button is pressed.
        """
        pull = self.pull()
        if pull == self.PULL_UP:
            return not self.value()
        elif pull == self.PULL_DOWN or pull is None:
            return self.value()
        else:
            raise NotImplementedError


class DebouncedLedPin(DebouncedPin):
    """Control a LED and read a switch with a single GPIO.

    Requires an additional resistor component for the switch.

    If the LED is activated; it will be turned off for an
    imperceivably short duration to read the switch state.

    Connections (PULL_UP)::

        GPIO -> 270Ω -> LED -> GND
             -> 10kΩ -> switch -> GND

    Connections (PULL_DOWN)::

        GPIO -> 270Ω -> LED -> Vcc
             -> 10kΩ -> switch -> Vcc

    * Adjust the LED resistor according to desired forward current.
    * The switch resistor should probably be in the range of 5k~20k.
    """

    def __init__(self, id, pull, *, value=None, period=20, timer_id=-1):
        super().__init__(id, pull=pull, value=value, period=period, timer_id=timer_id)
        self.init(Pin.OUT)

    def value(self, x=None):
        """Read debounced pin value.

        Will inherently be delayed to actual value by ``period`` ms.
        """
        if x is None:
            return self._val
        else:
            return Pin.value(self, x)

    def _timer_callback(self, timer):
        self.init(Pin.IN)
        super()._timer_callback(timer)
        self.init(Pin.OUT)
