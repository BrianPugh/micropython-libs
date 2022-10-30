import matplotlib.pyplot as plt
import pytest
from pid import PID
from pidautotune import AutotuneSuccess, PIDAutotune

from sim.watertank import WaterTank


class MockTime:
    def __init__(self, init=0):
        self.time = 0
        self.mock = None

    def __call__(self):
        return self.time


@pytest.fixture
def mock_time(mocker):
    mock_time = MockTime()
    mock_time.mock = mocker.patch("pidautotune.time_ms", side_effect=mock_time)
    return mock_time


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
        try:
            power_percent = controller(water_temperature)
        except AutotuneSuccess:
            break

        assert power_percent is not None

        ts.append(time)
        power_percents.append(power_percent)
        water_temperatures.append(water_temperature)
        targets.append(controller.setpoint)

    return ts, power_percents, water_temperatures, targets


def test_pid_autotune(mock_time):
    controller = PIDAutotune(setpoint=90, hysterisis=0.1)
    ts, power_percents, water_temperatures, targets = _simulate(mock_time, controller)

    results = {}
    predicted_tuning_pid = {
        "manual1": (0.1146, 0.00027, 0.08),
    }
    for tuning_rule in controller.tuning_rules:
        params = controller.compute_tunings(tuning_rule)
        predicted_tuning_pid[tuning_rule] = params
        print(f"{tuning_rule}: {params}")

    for tuning_rule, params in predicted_tuning_pid.items():
        results[tuning_rule] = {}
        exp_res = results[tuning_rule] = {}
        pid = PID(*params)
        pid.setpoint = 90
        ts, power_percents, water_temperatures, targets = _simulate(mock_time, pid)
        exp_res["ts"] = ts
        exp_res["power_percents"] = power_percents
        exp_res["water_temperatures"] = water_temperatures
        exp_res["targets"] = targets

    if False:
        fig = plt.figure()
        ax = fig.add_subplot(1, 2, 1)
        for tuning_rule, res in results.items():
            ax.plot(ts, res["water_temperatures"], label=f"{tuning_rule}")
        ax.plot(ts, targets, label="setpoint")
        ax.set_xlabel("Time (mS)")
        ax.set_ylabel("Water Temperature (c)")
        ax.set_title("Water Temperature")
        ax.legend(loc="lower right")

        ax = fig.add_subplot(1, 2, 2)
        for tuning_rule, res in results.items():
            ax.plot(ts, res["power_percents"], label=f"{tuning_rule}")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Power (%)")
        ax.set_title("Power")
        plt.show()
