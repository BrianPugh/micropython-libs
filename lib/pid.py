"""A simple and easy to use PID controller in Python.

Adapted from:
    https://github.com/m-lundberg/simple-pid
"""

import time

try:
    import micropython  # pyright: ignore[reportMissingImports]
except ImportError:
    micropython = None

if micropython:
    time_ms = time.ticks_ms  # pyright: ignore[reportGeneralTypeIssues]
    ticks_diff = time.ticks_diff  # pyright: ignore[reportGeneralTypeIssues]
else:
    time_ms = lambda: int(round(time.monotonic_ns() / 1_000_000))  # noqa: E731
    ticks_diff = lambda x, y: x - y  # noqa: E731


def _clamp(value, limits):
    lower, upper = limits
    if (upper is not None) and (value > upper):
        return upper
    elif (lower is not None) and (value < lower):
        return lower
    return value


class PID(object):
    """A simple PID controller."""

    def __init__(
        self,
        k_p=1.0,
        k_i=0.0,
        k_d=0.0,
        setpoint=0,
        period=0.01,
        output_limits=(0, 1),
        auto_mode=True,
        proportional_on_measurement=False,
        differetial_on_measurement=True,
        error_map=None,
    ):
        """
        Initialize a new PID controller.

        Parameters
        ----------
        k_p: float
            The value for the proportional gain Kp
        k_i: float
            The value for the integral gain Ki
        k_d: float
            The value for the derivative gain Kd
        setpoint: float
            The initial setpoint that the PID will try to achieve
        period: int
            The time in seconds which the controller should wait before generating
            a new output value. The PID works best when it is constantly called (eg. during a
            loop), but with a sample time set so that the time difference between each update is
            (close to) constant. If set to None, the PID will compute a new output value every time
            it is called.
        output_limits: tuple
            The initial output limits to use, given as an iterable with 2
            elements, for example: (lower, upper). The output will never go below the lower limit
            or above the upper limit. Either of the limits can also be set to None to have no limit
            in that direction. Setting output limits also avoids integral windup, since the
            integral term will never be allowed to grow outside of the limits.
        auto_mode: bool
            Whether the controller should be enabled (auto mode) or not (manual mode)
        proportional_on_measurement: bool
            Whether the proportional term should be calculated on
            the input directly rather than on the error (which is the traditional way). Using
            proportional-on-measurement avoids overshoot for some types of systems.
        differetial_on_measurement: bool
            Whether the differential term should be calculated on
            the input directly rather than on the error (which is the traditional way).
        error_map: Callable
            Function to transform the error value in another constrained value.
        """
        self.k_p, self.k_i, self.k_d = k_p, k_i, k_d
        self.setpoint = setpoint
        self.period = period

        self._min_output, self._max_output = None, None
        self._auto_mode = auto_mode
        self.proportional_on_measurement = proportional_on_measurement
        self.differetial_on_measurement = differetial_on_measurement
        self.error_map = error_map

        self._proportional = 0
        self._integral = 0
        self._derivative = 0

        self._last_time = time_ms()
        self._last_output = None
        self._last_error = None
        self._last_input = None

        self.output_limits = output_limits
        self.reset()

    def __call__(self, input_, dt=None):
        """
        Update the PID controller.

        Call the PID controller with *input_* and calculate and return a control output if
        ``period`` seconds has passed since the last update. If no new output is calculated,
        return the previous output instead (or None if no value has been calculated yet).

        Parameters
        ----------
        input_: float
            Sensor value
        dt: Optional[float]
            If set, uses this value for timestep (milliseconds) instead of real time.
            This can be used in simulations when simulation time is different from real time.

        Returns
        -------
        float
            Control variable (what the output actuator should be set to).

        """
        if not self.auto_mode:
            return self._last_output

        now = time_ms()
        if dt is None:
            dt = ticks_diff(now, self._last_time)
        elif dt < 0:
            raise ValueError("dt has negative value {}, must be positive".format(dt))

        dt /= 1000  # dt is now in seconds

        if (
            self.period is not None
            and dt < self.period
            and self._last_output is not None
        ):
            # Only update every period seconds
            return self._last_output

        # Compute error terms
        error = self.setpoint - input_
        d_input = input_ - (
            self._last_input if (self._last_input is not None) else input_
        )
        d_error = error - (
            self._last_error if (self._last_error is not None) else error
        )

        # Check if must map the error
        if self.error_map is not None:
            error = self.error_map(error)

        # Compute the proportional term
        if not self.proportional_on_measurement:
            # Regular proportional-on-error, simply set the proportional term
            self._proportional = self.k_p * error
        else:
            # Add the proportional error on measurement to error_sum
            self._proportional -= self.k_p * d_input

        output = self._proportional
        # Compute integral and derivative terms
        if self._last_output is not None:
            self._integral += self.k_i * error * dt
            self._integral = _clamp(
                self._integral, self.output_limits
            )  # Avoid integral windup

            if self.differetial_on_measurement:
                self._derivative = -self.k_d * d_input / dt
            else:
                self._derivative = self.k_d * d_error / dt

            # Compute final output
            output += self._integral + self._derivative

        output = _clamp(output, self.output_limits)

        # Keep track of state
        self._last_output = output
        self._last_input = input_
        self._last_error = error
        self._last_time = now

        return output

    def __repr__(self):
        return (
            "{self.__class__.__name__}("
            "Kp={self.k_p!r}, Ki={self.k_i!r}, Kd={self.k_d!r}, "
            "setpoint={self.setpoint!r}, period={self.period!r}, "
            "output_limits={self.output_limits!r}, auto_mode={self.auto_mode!r}, "
            "proportional_on_measurement={self.proportional_on_measurement!r}, "
            "differetial_on_measurement={self.differetial_on_measurement!r}, "
            "error_map={self.error_map!r}"
            ")"
        ).format(self=self)

    @property
    def components(self):
        """PID Components.

        The P-, I- and D-terms from the last computation as separate components as a tuple. Useful
        for visualizing what the controller is doing or when tuning hard-to-tune systems.
        """
        return self._proportional, self._integral, self._derivative

    @property
    def tunings(self):
        """Tunings used by the controller as a tuple: (Kp, Ki, Kd)."""
        return self.k_p, self.k_i, self.k_d

    @tunings.setter
    def tunings(self, tunings):
        """Set the PID tunings."""
        self.k_p, self.k_i, self.k_d = tunings

    @property
    def auto_mode(self):
        """Whether the controller is currently enabled (in auto mode) or not."""
        return self._auto_mode

    @auto_mode.setter
    def auto_mode(self, enabled):
        """Enable or disable the PID controller."""
        self.set_auto_mode(enabled)

    def set_auto_mode(self, enabled, last_output=None):
        """
        Enable or disable the PID controller, optionally setting the last output value.

        This is useful if some system has been manually controlled and if the PID should take over.
        In that case, disable the PID by setting auto mode to False and later when the PID should
        be turned back on, pass the last output variable (the control variable) and it will be set
        as the starting I-term when the PID is set to auto mode.

        :param enabled: Whether auto mode should be enabled, True or False
        :param last_output: The last output, or the control variable, that the PID should start
            from when going from manual mode to auto mode. Has no effect if the PID is already in
            auto mode.
        """
        if enabled and not self._auto_mode:
            # Switching from manual mode to auto, reset
            self.reset()

            self._integral = last_output if (last_output is not None) else 0
            self._integral = _clamp(self._integral, self.output_limits)

        self._auto_mode = enabled

    @property
    def output_limits(self):
        """Output limits as a 2-tuple: (lower, upper).

        See also the *output_limits* parameter in :meth:`PID.__init__`.
        """
        return self._min_output, self._max_output

    @output_limits.setter
    def output_limits(self, limits):
        """Set the output limits."""
        if limits is None:
            self._min_output, self._max_output = None, None
            return

        min_output, max_output = limits

        if (None not in limits) and (max_output < min_output):
            raise ValueError("lower limit must be less than upper limit")

        self._min_output, self._max_output = min_output, max_output

        if self._integral is not None:
            self._integral = _clamp(self._integral, self.output_limits)
        if self._last_output is not None:
            self._last_output = _clamp(self._last_output, self.output_limits)

    def reset(self):
        """
        Reset the PID controller internals.

        This sets each term to 0 as well as clearing the integral, the last output and the last
        input (derivative calculation).
        """
        self._proportional = 0
        self._integral = 0
        self._derivative = 0
        self._integral = _clamp(self._integral, self.output_limits)
        self._last_time = time_ms()
        self._last_output = None
        self._last_input = None
