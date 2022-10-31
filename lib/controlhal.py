"""Abstractions for controlling a dynamic system.

Dependencies:

Optional dependencies:
    * ``ringbuffer`` if ``Derivative`` is used.
    * ``pid`` if ``ControlLoop`` class is used.
    * ``pidautotune`` if autotune capabilities of ``ControlLoop`` are used.
"""
import time

try:
    import micropython  # pyright: ignore[reportMissingImports]
except ImportError:
    micropython = None

if micropython:
    time_ms = time.ticks_ms  # pyright: ignore[reportGeneralTypeIssues]
    ticks_diff = time.ticks_diff  # pyright: ignore[reportGeneralTypeIssues]
    const = micropython.const
else:
    time_ms = lambda: int(round(time.monotonic_ns() / 1_000_000))  # noqa: E731
    ticks_diff = lambda x, y: x - y  # noqa: E731
    const = lambda x: x  # noqa: E731


def check_type(obj, cls):
    if not isinstance(obj, cls):
        raise ValueError(f"Expected {cls.__name__}")
    return obj


class Peripheral:
    def __init__(self, period=None):
        """Abstract IO class.

        Abstraction layer for any sensor (input) or actuator (output).

        Parameters
        ----------
        period: Optional[float]
            Perform actions every this many seconds.
            Defaults to 0.01 seconds.
        """
        if period is None:
            period = 0.01
        elif period <= 0:
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
            or ticks_diff(now, self._last_action_time) > 1000 * self.period
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

    @staticmethod
    def _convert(val):
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

        super().__init__(period=sensor.period)
        self._sensor = sensor
        self._buffer = RingBuffer(5)

    def read(self):
        if self._should_perform_action():
            buffer = self._buffer
            buffer.append(self._sensor.read())

            if self._buffer.full:
                # Five-point stencil 1D Derivative
                self._last_read = (
                    buffer[0]  # -2h
                    - 8 * buffer[1]  # -1h
                    + 8 * buffer[3]  # 1h
                    - buffer[4]  # 2h
                ) / (12 * self.period)

        return self._last_read


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
        if self._should_perform_action():
            if not (0 <= val <= 1):
                raise ValueError
            self.raw_write(val)

    def raw_write(self, val):
        """Write ``val`` to actuator.

        Parameters
        ----------
        val : float
            Value to write in range ``[0, 1]``.
        """
        raise NotImplementedError


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
        self.actuator = check_type(actuator, Actuator)
        self.sensor = check_type(sensor, Sensor)

        from pid import PID

        if isinstance(pid, PID):
            self.pid = pid
        else:
            self.pid = PID(
                *pid,
                output_limits=(0, 1),
                period=max(actuator.period, sensor.period),
            )
        self.autotuner = None

        self.set_mode_normal()

    def set_mode_autotune(self, setpoint, **kwargs):
        """Change operating mode to autotune.

        See ``PIDAutotune`` for docs.
        """
        if self.mode == self.MODE_AUTOTUNE:
            raise Exception
        from pidautotune import PIDAutotune

        self.mode = self.MODE_AUTOTUNE
        self.autotuner = PIDAutotune(setpoint, period=self.pid.period, **kwargs)
        self.pid.set_auto_mode(False)

    def set_mode_normal(self):
        self.pid.set_auto_mode(True)
        self.mode = self.MODE_NORMAL

    @property
    def tunings(self):
        if self.mode == self.MODE_NORMAL:
            return self.pid.tunings
        else:
            raise Exception

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
        return self.actuator is other.actuator and self.sensor is other.sensor

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
