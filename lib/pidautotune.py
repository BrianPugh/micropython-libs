"""A simple and easy to use PID controller in Python.

Adapted from:
    https://github.com/hirschmann/pid-autotune/blob/master/autotune.py

Depends on:
    * ringbuffer
"""

import time
from collections import namedtuple
from math import pi

from controlhal import AutotuneFailure, AutotuneSuccess, Controller
from ringbuffer import RingBuffer

try:
    import micropython  # pyright: ignore[reportMissingImports]
except ImportError:
    micropython = None

if micropython:
    time_ms = time.ticks_ms  # pyright: ignore[reportGeneralTypeIssues]
    ticks_diff = time.ticks_diff  # pyright: ignore[reportGeneralTypeIssues]
    const = micropython.const
else:  # pragma: no cover
    time_ms = lambda: int(round(time.monotonic_ns() / 1_000_000))  # noqa: E731
    ticks_diff = lambda x, y: x - y  # noqa: E731
    const = lambda x: x  # noqa: E731


TuningRuleCoeffs = namedtuple("TuningRuleCoeffs", ("k_p", "t_i", "t_d"))


def _clamp(value, limits):
    lower, upper = limits
    if (upper is not None) and (value > upper):
        return upper
    elif (lower is not None) and (value < lower):
        return lower
    return value


class PIDAutotune(Controller):
    PEAK_AMPLITUDE_TOLERANCE = 0.05  # [0, 1] percent

    STATE_OFF = const(0)
    STATE_RELAY_STEP_UP = const(1)
    STATE_RELAY_STEP_DOWN = const(2)
    STATE_SUCCEEDED = const(3)
    STATE_FAILED = const(4)

    _tuning_coeffs = {
        "ziegler-nichols-p": TuningRuleCoeffs(0.5, 0.0, 0.0),
        "ziegler-nichols-pi": TuningRuleCoeffs(0.45, 5 / 6, 0.0),
        "ziegler-nichols-pid": TuningRuleCoeffs(0.6, 0.5, 1 / 8),
        "some-overshoot": TuningRuleCoeffs(1 / 3, 0.5, 1 / 3),
        "no-overshoot": TuningRuleCoeffs(0.2, 0.5, 1 / 3),
        "tyreus-luyben": TuningRuleCoeffs(1 / 3.2, 2.2, 1 / 6.3),
    }

    def __init__(
        self,
        setpoint,
        hysterisis,
        initial_output=0,
        output_step=1.0,  # 100%
        period=0.01,
        lookback=16,
        output_limits=(0, 1),
        max_cycles=10,
        method="some-overshoot",
    ):
        """Estimate viable parameters for a PID controller.

        Åström-Hägglund relay tuning method

        Adapted from:
            https://github.com/hirschmann/pid-autotune/blob/master/autotune.py
            https://d1.amobbs.com/bbs_upload782111/files_36/ourdev_614499E39LAH.pdf

        Parameters
        ----------
        setpoint: float
            The target process (sensor) value.
        hysterisis: float
            Maximum expected noise from sensor.
            For example, if your thermocouple reports ±0.5°C, this value should be
            slightly higher, like ``0.6``.
        initial_output: float
            Initial control (actuator) output value.
            Output control value will be centered around this value.
        output_step: float
            The value by which the output will be increased/decreased when stepping up/down.
        period: float
            The time in seconds which the controller should wait before generating
            a new output value.
        lookback: int
            Number of samples to lookback to determine local minima/maxima.
        output_limits: tuple
            The initial output limits to use, given as an iterable with 2
            elements, for example: (lower, upper). The output will never go below the lower limit
            or above the upper limit. Either of the limits can also be set to None to have no limit
            in that direction.
        max_cycles: int
            Maximum number of times to control cycle before aborting autotune process due to
            measurement instability.
        method:
            Default tuning method coefficients used when ``AutotuneSuccess`` is raised.
        """
        if method not in self._tuning_coeffs:
            raise ValueError

        self.method = method
        self.hysterisis = hysterisis
        self._inputs = RingBuffer(lookback)
        self.output_step = output_step
        self.output_limits = output_limits
        self.max_cycles = max_cycles

        self._state = PIDAutotune.STATE_OFF
        self._peaks = RingBuffer(5)  # sensor values at detected peaks
        self._peak_timestamps = RingBuffer(
            5, dtype="Q"
        )  # timestamp in mS at detected peaks

        self._output = 0
        self._proposed_peak_type = 0
        self._peak_count = 0
        self._initial_output = 0
        self._ultimate_gain = 0
        self._ultimate_period = 0

        self._output_range = _clamp(
            self._initial_output + self.output_step, output_limits
        ) - _clamp(self._initial_output - self.output_step, output_limits)

        super().__init__(setpoint=setpoint, period=period)

    def reset(self):
        self._state = PIDAutotune.STATE_OFF

    @property
    def output(self):
        """Get the last output value."""
        return self._output

    @property
    def tuning_rules(self):
        """Get a list of all available tuning rules."""
        return self._tuning_coeffs.keys()

    @property
    def parameters(self):
        return self.compute_tunings()

    def compute_tunings(self, tuning_rule=None):
        """Get PID parameters.

        Parameters
        ----------
        tuning_rule: str
            Rule to calculate the PID parameters.
        """
        if tuning_rule is None:
            tuning_rule = self.method
        coeffs = self._tuning_coeffs[tuning_rule]
        k_p = coeffs.k_p * self._ultimate_gain
        k_i = k_p / (coeffs.t_i * self._ultimate_period) if coeffs.t_i else 0
        k_d = k_p * (coeffs.t_d * self._ultimate_period) if coeffs.t_d else 0
        return k_p, k_i, k_d

    def __call__(self, input_val):
        """Update the autotune system.

        To be called periodically

        Parameters
        ----------
        input_val: float
            Sensor value

        Raises
        ------
        AutotuneSuccess
            Autotuning is complete and was successful.
            Use ``autotuner.get_pid_parameters()`` to get results.
        AutotuneFailure
            Autotuning is complete and was not successful.

        Returns
        -------
        float
            Control variable (what the output actuator should be set to).
        """
        now = time_ms()
        if (
            self._state == PIDAutotune.STATE_OFF
            or self._state == PIDAutotune.STATE_SUCCEEDED
            or self._state == PIDAutotune.STATE_FAILED
        ):
            self._init_tuner(input_val, now)
        elif ticks_diff(now, self._last_action_time) < 1000 * self.period:
            return self.output

        self._last_action_time = now

        # check input and change relay state if necessary
        if (
            self._state == PIDAutotune.STATE_RELAY_STEP_UP
            and input_val > self.setpoint + self.hysterisis
        ):
            self._state = PIDAutotune.STATE_RELAY_STEP_DOWN
        elif (
            self._state == PIDAutotune.STATE_RELAY_STEP_DOWN
            and input_val < self.setpoint - self.hysterisis
        ):
            self._state = PIDAutotune.STATE_RELAY_STEP_UP

        # set output
        if self._state == PIDAutotune.STATE_RELAY_STEP_UP:
            self._output = self._initial_output + self.output_step
        elif self._state == PIDAutotune.STATE_RELAY_STEP_DOWN:
            self._output = self._initial_output - self.output_step

        # respect output limits
        self._output = _clamp(self._output, self.output_limits)

        if self._inputs:
            # identify peaks
            is_max = input_val > self._inputs.max()
            is_min = input_val < self._inputs.min()
        else:
            is_max = is_min = True

        self._inputs.append(input_val)

        # we don't want to trust the maxes or mins until the input array is full
        if not self._inputs.full:
            return self.output

        # increment peak count and record peak time for maxima and minima
        inflection = False

        # peak types:
        # -1: minimum
        # +1: maximum
        if is_max:
            if self._proposed_peak_type == -1:
                inflection = True
            self._proposed_peak_type = 1
        elif is_min:
            if self._proposed_peak_type == 1:
                inflection = True
            self._proposed_peak_type = -1

        # update peak times and values
        if inflection:
            self._peak_count += 1
            self._peaks.append(input_val)
            self._peak_timestamps.append(now)

        # check for convergence of induced oscillation
        # convergence of amplitude assessed on last 4 peaks (1.5 cycles)
        amplitude_pp = 0

        if inflection and (self._peak_count > 4):
            amplitude_pp_max = self._peaks.max() - self._peaks.min()
            n_amplitudes = len(self._peaks) - 1

            # compute the average peak-to-peak amplitude
            for i in range(n_amplitudes):
                # peak-to-peak amplitude
                amplitude_pp += abs(self._peaks[i] - self._peaks[i + 1])
            amplitude_pp /= n_amplitudes

            # check convergence criterion for amplitude of induced oscillation
            amplitude_dev = (amplitude_pp_max - amplitude_pp) / amplitude_pp
            if amplitude_dev < self.PEAK_AMPLITUDE_TOLERANCE:
                self._state = PIDAutotune.STATE_SUCCEEDED

        if self._state == PIDAutotune.STATE_SUCCEEDED:
            self._output = 0

            # calculate ultimate gain
            self._ultimate_gain = (4 * amplitude_pp) / (pi * self._output_range)

            # calculate ultimate period in seconds
            ultimate_period = 0
            n_periods = len(self._peaks) - 2
            for i in range(0, n_periods):
                ultimate_period += ticks_diff(
                    self._peak_timestamps[i + 2], self._peak_timestamps[i]
                )
            # Average period, convert milliseconds -> seconds
            ultimate_period /= 1000 * n_periods
            self._ultimate_period = ultimate_period
            raise AutotuneSuccess(self.compute_tunings(self.method))
        elif self._peak_count >= 2 * self.max_cycles:
            # if the autotune has not already converged, terminate
            self._output = 0
            self._state = PIDAutotune.STATE_FAILED
            raise AutotuneFailure

        return self.output

    def _init_tuner(self, input_value, timestamp):
        self._proposed_peak_type = 0
        self._peak_count = 0
        self._output = 0
        self._initial_output = 0
        self._ultimate_gain = 0
        self._ultimate_period = 0
        self._inputs.clear()
        self._peaks.clear()
        self._peak_timestamps.clear()
        self._peak_timestamps.append(timestamp)
        self._state = PIDAutotune.STATE_RELAY_STEP_UP
