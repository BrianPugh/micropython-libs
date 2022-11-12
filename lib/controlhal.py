"""Abstractions for controlling a dynamic system.

Optional dependencies:
    * ``ringbuffer`` if ``Derivative`` is used.
    * ``pid`` if ``ControlLoop`` class is used.
    * ``pidautotune`` if autotune capabilities of ``ControlLoop`` are used.

Typical usecase:

.. code-block:: python

    import machine
    from controlhal import Sensor, Actuator, ControlLoop


    class Heater(Actuator):
        def __init__(self, pin, period=None):
            super().__init__(period=period)
            self.pwm = machine.PWM(pin)

        def _raw_write(self, val):
            # 0 == off, 1023 == on
            self.pwm.duty(round(val * 1023))


    class Thermometer(Actuator):
        def __init__(self, pin, period=None):
            super().__init__(period=period)
            self.adc = machine.ADC(pin)

        def _raw_read(self, val):
            # 0 == fully low-signal, 65535 = fully high-signal.
            return self.adc.read_u16()

        def _convert(self, val):
            # Example conversion from u16 from adc to celsius.
            return 100 * (val / 65535) + 17


    heater = Heater(12)
    thermometer = Thermometer(0)
    boiler = ControlLoop(heater, thermometer, pid=(0.1, 0.002, 0.08))
    boiler.write(90)  # Assign setpoint to 90 degrees celsius
    while True:
        boiler()  # update feedback loop
"""
import time

try:
    import micropython  # pyright: ignore[reportMissingImports]
except ModuleNotFoundError:
    micropython = None

try:
    from pid import PID
except ModuleNotFoundError:
    PID = None

try:
    from pidautotune import PIDAutotune
except ModuleNotFoundError:
    PIDAutotune = None

if micropython:
    from machine import Timer  # pyright: ignore[reportMissingImports]

    time_ms = time.ticks_ms  # pyright: ignore[reportGeneralTypeIssues]
    ticks_diff = time.ticks_diff  # pyright: ignore[reportGeneralTypeIssues]
    const = micropython.const
else:  # pragma: no cover
    Timer = None
    time_ms = lambda: int(round(time.monotonic_ns() / 1_000_000))  # noqa: E731
    ticks_diff = lambda x, y: x - y  # noqa: E731
    const = lambda x: x  # noqa: E731

# For mitigating floating-point nonsense
_eps = const(1e-5)


def check_type(obj, cls):
    if not isinstance(obj, cls):
        raise ValueError(f"Expected {cls.__name__}")
    return obj


class Peripheral:
    default_period = 0.01

    def __init__(self, period=None):
        """Abstract IO class.

        Abstraction layer for any sensor (input) or actuator (output).
        Should probably **not** be directly subclassed by user code;
        see ``Sensor`` and ``Actuator`` for most use-cases.

        Parameters
        ----------
        period: Optional[float]
            Perform actions every this many seconds.
            Defaults to 0.01 seconds.
        """
        if period is None:
            period = self.default_period
        elif period < 0:
            raise ValueError
        self.period = period
        self._last_action_time = None

    def _should_perform_action(self):
        """Enough has time has elapsed than an action should be performed.

        Not idempotent; internally updates ``_last_action_time`` state.

        Returns
        -------
        bool
            ``True`` if an action should be performed.
        """
        now = time_ms()
        if (
            self._last_action_time is None
            or ticks_diff(now, self._last_action_time) >= 1000 * self.period
        ):
            self._last_action_time = now
            return True
        return False


class Sensor(Peripheral):
    def __init__(self, period=None, samples=1):
        """Abstract input sensor class.

        Parameters
        ----------
        period: Optional[float]
            Perform actual reads every this many seconds.
            Calling ``read`` prior to this period will return previous value.
        samples: int
            Sample this many times and average them per read.
        """
        super().__init__(period=period)
        self._samples = samples
        self._last_read = 0

    def read(self):
        """Oversample sensor, and convert to appropriate value."""
        if self._should_perform_action():
            val = sum(self._raw_read() for _ in range(self._samples))
            val /= self._samples
            self._last_read = self._convert(val)
        return self._last_read

    def _raw_read(self):
        """Read sensor.

        To be implemented by subclass.
        Only to be called in ``Sensor.read`` and not for external use.

        Returns
        -------
        float
        """
        raise NotImplementedError

    def _convert(self, val):
        """Convert raw-value from ``_raw_read`` to a SI base unit float.

        Used to only call conversion once per oversample, rather than once per sample.

        Reference:
            https://en.wikipedia.org/wiki/SI_base_unit


        To be implemented by subclass.
        Only to be called in ``Sensor.read`` and not for external use.

        Parameters
        ----------
        val : Number

        Returns
        -------
        float
        """
        return val


class Derivative(Sensor):
    def __init__(self, sensor):
        """Time-derivative of a sensor.

        Parameters
        ----------
        sensor: Sensor
            sensor we want the derivative of.
        """
        from ringbuffer import RingBuffer

        if sensor.period == 0:
            raise ValueError("Cannot take the derivative of a sensor with 0 period.")

        super().__init__(period=sensor.period)
        self._sensor = sensor
        self._val_buffer = RingBuffer(5)
        self._time_buffer = RingBuffer(5)

    def read(self):
        if self._should_perform_action():
            val_buffer, time_buffer = self._val_buffer, self._time_buffer

            val_buffer.append(self._sensor.read())
            time_buffer.append(time_ms())

            if self._val_buffer.full:
                # Five-point stencil 1D Derivative Approximation
                dt4 = sum(
                    ticks_diff(time_buffer[i + 1], time_buffer[i])
                    for i in range(len(time_buffer) - 1)
                )

                # 5-point stencil has a denominator of 12h
                # We sum the 4 time differences, so this becomes 3h
                # To need to convert ms -> s, so this becomes 0.003h
                self._last_read = (
                    val_buffer[0]  # -2h
                    - 8 * val_buffer[1]  # -1h
                    + 8 * val_buffer[3]  # 1h
                    - val_buffer[4]  # 2h
                ) / (0.003 * dt4)

        return self._last_read


class ADCSensor(Sensor):
    def __init__(self, adc, m=1 / 65535, b=0.0, period=None):
        """ADC Sensor.

        Parameters
        ----------
        adc: machine.ADC
            Configured ADC object.
        m: float
            Multiply the u16 adc reading by this.
            Defaults to ``1/65535`` (normalizes reading to range [0, 1.0])
        b : float
            Add this to the reading after ``m`` is applied.
            Defaults to ``0.0``.
        """
        super().__init__(period=period)
        self.adc = adc
        self.m = m
        self.b = b

    def _raw_read(self):
        return self.adc.read_u16()

    def _convert(self, val):
        return val * self.m + self.b


class Actuator(Peripheral):
    def __init__(self, period=None):
        """Abstract output actuator class.

        Parameters
        ----------
        period: Optional[float]
            Perform actual writes every this many seconds.
            Calling ``write`` prior to this period will not perform a write.
        """
        super().__init__(period=period)
        self._setpoint = 0

    @property
    def setpoint(self):
        return self._setpoint

    def write(self, val):
        """Write ``val`` to actuator.

        Parameters
        ----------
        val : float
            Value to write in range ``[0, 1]``.

        Returns
        -------
        None
        """
        if not (0 <= val <= 1):
            raise ValueError

        if self._should_perform_action():
            self._setpoint = val
            self._raw_write(val)

    def read(self):
        return self.setpoint

    def _raw_write(self, val):
        """Perform actual write ``val`` to actuator.

        Parameters
        ----------
        val : float
            Value to write in range ``[0, 1]``.
        """
        raise NotImplementedError


class TimeProportionalActuator(Actuator):
    def __init__(self, pin=None, period=10.0, invert=False, timer_id=-1):
        """Create a TimeProportionalActuator object.

        Cycle actuators are for controlling binary actuators that have an associated switching cost.
        For example, if a physical relay is controlling a heater, a cycle_period of 10s might
        be chosen to extend the life of the relay. If 60% power is requested, then the relay
        will be on for 6 consecutive seconds, then off for 4 consecutive seconds.

        Parameter
        ---------
        pin: Optional[machine.Pin]
            If provided, performs digital writes to it.
            Provided ``Pin`` must be configured to ``Pin.OUT`` mode.
        period: float
            Time in seconds for a cycle.
            Defaults to ``10.0`` seconds.
            Minimum value is ``0.1``; if a faster ``cycle_period`` is desired, look into PWM.
        timer_id : int
            Physical Timer ID to use. Defaults to ``-1`` (virtual timer).
        invert: bool
            Invert writes to provided ``pin``.
            I.e. device has ``0`` for on and ``1`` for off.
            Does nothing if ``pin`` is not provided.
        """
        if period < 0.1:
            raise ValueError("cycle_period must be at least 0.1 seconds.")

        super().__init__(period=period)

        self.pin = pin
        self.invert = invert

        self._period_ms = int(1000 * period)
        self._setpoint_int = 0  # Integer percent in range [0, 100]
        self._last_action = False
        self._counter = 0

        self._timer = Timer(timer_id)  # pyright: ignore[reportOptionalCall]
        # period is in seconds; timer.init expects mS.
        # This timer will execute 100 times per period.
        self._timer.init(period=10 * period, callback=self._timer_callback)

    @property
    def setpoint(self):
        return self._setpoint_int / 100

    @setpoint.setter
    def setpoint(self, val):
        self._setpoint_int = round(100 * val)

    def _timer_callback(self, timer):
        if self._counter == 0:
            # only activate on 0 to prevent rapid toggling if
            # setpoint is increased as ~same-rate as counter.
            if self._counter < self._setpoint_int:
                if not self._last_action:
                    self._raw_write(1)
                    self._last_action = True
        else:
            if self._last_action and self._counter >= self._setpoint_int:
                self._raw_write(0)
                self._last_action = False
        self._counter = (self._counter + 1) % 100

    def write(self, val):
        if not (0 <= val <= 1):
            raise ValueError
        self.setpoint = val

    def _raw_write(self, val):
        if self.pin is None:
            return
        val = bool(val)
        if self.invert:
            val = not val
        self.pin(val)


class PWMActuator(Actuator):
    def __init__(self, pwm, period=None):
        """PWM Actuator.

        Parameters
        ----------
        pwm: machine.PWM
            Configured PWM object.
        """
        super().__init__(period=0)
        if period is not None:
            pwm.freq(round(1 / period))

        self.pwm = pwm

    def _raw_write(self, val):
        self.pwm.duty_u16(round(val * 65535))


class ControlLoop(Peripheral):
    MODE_NORMAL = const(0)
    MODE_AUTOTUNE = const(1)

    def __init__(self, actuator, sensor, pid=(1.0, 0.0, 0.0)):
        """Create a control loop.

        Parameters
        ----------
        actuator: Actuator
        sensor: Optional[Sensor]
        pid: Union[tuple, PID]
            If a tuple, a PID object will be created from these tunings.
            If a PID object, will directly be used.
        """
        if PID is None:
            raise ModuleNotFoundError("No module named 'pid'")  # pragma: no cover
        self.actuator = check_type(actuator, Actuator)
        self.sensor = check_type(sensor, Sensor)

        if isinstance(pid, tuple):
            self.pid = PID(
                *pid,
                output_limits=(0, 1),
                period=max(actuator.period, sensor.period),
            )
        else:
            self.pid = pid
        self.autotuner = None

        self.set_mode_normal()

    def set_mode_autotune(self, setpoint, **kwargs):
        """Change operating mode to autotune.

        See ``PIDAutotune`` for docs.
        """
        if PIDAutotune is None:
            raise ModuleNotFoundError(
                "No module named 'pidautotune'"
            )  # pragma: no cover

        if self.mode == self.MODE_AUTOTUNE:
            return

        self.mode = self.MODE_AUTOTUNE
        self.autotuner = PIDAutotune(setpoint, period=self.pid.period, **kwargs)
        self.pid.set_auto_mode(False)

    def set_mode_normal(self):
        self.pid.set_auto_mode(True)
        self.mode = self.MODE_NORMAL

    @property
    def tunings(self):
        return self.pid.tunings

    def compute_tunings(self, *args, **kwargs):
        if self.mode == self.MODE_NORMAL:
            return self.pid.tunings
        elif self.mode == self.MODE_AUTOTUNE:
            if self.autotuner is None:
                raise Exception
            return self.autotuner.compute_tunings(*args, **kwargs)
        else:
            raise NotImplementedError

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        return (
            self.actuator is other.actuator
            and self.sensor is other.sensor
            and (self.tunings == other.tunings)
        )

    def read(self):
        """Read sensor.

        Note: not symmetrical to ``write``; returns last sensor value, not setpoint.
        """
        return self.sensor.read()

    def write(self, val):
        """Set target setpoint.

        Here to have the same interface as an actuator.

        Note: not symmetrical to ``read``; doesn't directly write to actuator.
        """
        self.setpoint = val

    @property
    def setpoint(self):
        """Get target setpoint."""
        return self.pid.setpoint

    @setpoint.setter
    def setpoint(self, val):
        """Set target setpoint."""
        self.pid.setpoint = val

    def __call__(self):
        """Update feedback loop."""
        if self.mode == self.MODE_NORMAL:
            controller = self.pid
        elif self.mode == self.MODE_AUTOTUNE:
            if self.autotuner is None:
                raise Exception
            controller = self.autotuner
        else:
            raise NotImplementedError

        val = self.read()
        power_target = controller(val)
        self.actuator.write(power_target)
