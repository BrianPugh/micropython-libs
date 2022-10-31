import matplotlib.pyplot as plt
import numpy as np
import pytest
from common import MockTime
from pid import PID

from sim.watertank import WaterTank


@pytest.fixture
def mock_time(mocker):
    return MockTime.patch(mocker, "pid.time_ms")


def _simulate(mock_time, controller):
    max_power_kw = 1.3
    tank = WaterTank(delay=200)  # 2 Seconds
    power_percent = 0
    targets = [controller.setpoint]
    water_temperatures = [tank.temperature]
    ts = [0.0]
    power_percents = [0.0]
    for time in range(20_000):
        time *= 10  # time in mS
        mock_time.time = time

        water_temperature = tank.heat_cool(
            max_power_kw * power_percent,
            duration=0.01,  # 10 mS
            heat_loss_factor=20,
        )

        power_percent = controller(water_temperature)
        assert power_percent is not None

        ts.append(time)
        power_percents.append(power_percent)
        water_temperatures.append(water_temperature)
        targets.append(controller.setpoint)

    return ts, power_percents, water_temperatures, targets


def _plot_simulation(ts, power_percents, water_temperatures, targets):
    if False:
        fig = plt.figure()
        ax = fig.add_subplot(1, 2, 1)
        ax.plot(ts, water_temperatures, label="temperature")
        ax.plot(ts, targets, label="setpoint")
        ax.set_xlabel("Time (mS)")
        ax.set_ylabel("Water Temperature (c)")
        ax.set_title("Water Temperature")
        ax.legend(loc="lower right")

        ax = fig.add_subplot(1, 2, 2)
        ax.plot(ts, power_percents)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Power (%)")
        ax.set_title("Power")
        plt.show()


def test_pid_basic(mock_time, assert_array_equal):
    """Explicit test of the Boiler simulator with PID."""
    controller = PID(0.1146, 0.00027, 0.08)
    controller.setpoint = 90
    ts, power_percents, water_temperatures, targets = _simulate(mock_time, controller)
    _plot_simulation(ts, power_percents, water_temperatures, targets)
    assert_array_equal(np.array([ts, water_temperatures, power_percents]).transpose())

    controller.components
    controller.tunings = 1.0, 0.1, 0.0


def test_pid_set_limits():
    controller = PID(0.1146, 0.00027, 0.08, output_limits=None)
    controller.setpoint = 90
    _simulate(mock_time, controller)
    with pytest.raises(ValueError):
        # lower greater than higher
        PID(output_limits=(1.0, 0.5))


def test_pid_automode_off(mock_time):
    controller = PID(0.1146, 0.00027, 0.08)
    controller.setpoint = 90
    controller.auto_mode = False
    assert controller(20) is None

    controller.auto_mode = True
    assert controller(20) is not None
