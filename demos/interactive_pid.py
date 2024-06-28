import sys

sys.path.insert(0, "lib")

from unittest.mock import patch

import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from pid import PID

from sim.watertank import WaterTank


class MockTime:
    def __init__(self, init=0):
        self.time = 0
        self.mock = None

    def __call__(self):
        return self.time


mock_time = MockTime()


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

        ts.append(time / 1000)
        power_percents.append(power_percent)
        water_temperatures.append(water_temperature)
        targets.append(controller.setpoint)

    return ts, power_percents, water_temperatures, targets


@patch("pid.time_ms", new_callable=MockTime)
def main(mock_time):
    initial_p, initial_i, initial_d = 0.1, 0, 0
    controller = PID(initial_p, initial_i, initial_d)
    controller.setpoint = 90

    ts, power_percents, water_temperatures, targets = _simulate(mock_time, controller)

    fig = plt.figure()
    ax_temp = fig.add_subplot(1, 2, 1)
    (plot_temp,) = ax_temp.plot(ts, water_temperatures, label="temperature")
    ax_temp.plot(ts, targets, label="setpoint")
    ax_temp.set_ylim(0, 110)
    ax_temp.set_xlabel("Time (mS)")
    ax_temp.set_ylabel("Water Temperature (c)")
    ax_temp.set_title("Water Temperature")
    ax_temp.legend(loc="lower right")

    ax_power = fig.add_subplot(1, 2, 2)
    (plot_power,) = ax_power.plot(ts, power_percents)
    ax_power.set_ylim(-0.05, 1.05)
    ax_power.set_xlabel("Time (s)")
    ax_power.set_ylabel("Power (%)")
    ax_power.set_title("Power")

    # Make a horizontal slider to control the frequency.
    ax_p = fig.add_axes([0.25, 0.0, 0.65, 0.03])
    ax_i = fig.add_axes([0.25, 0.05, 0.65, 0.03])
    ax_d = fig.add_axes([0.25, 0.1, 0.65, 0.03])
    slider_p = Slider(
        ax=ax_p,
        label="Proportional",
        valmin=0.001,
        valmax=0.5,
        valinit=initial_p,
    )
    slider_i = Slider(
        ax=ax_i,
        label="Integral",
        valmin=0.000,
        valmax=0.01,
        valinit=initial_i,
    )
    slider_d = Slider(
        ax=ax_d,
        label="Derivative",
        valmin=0.000,
        valmax=1.0,
        valinit=initial_d,
    )

    # The function to be called anytime a slider's value changes
    def update(val):
        controller.reset()
        controller.parameters = (slider_p.val, slider_i.val, slider_d.val)
        ts, power_percents, water_temperatures, targets = _simulate(mock_time, controller)
        plot_temp.set_ydata(water_temperatures)
        plot_power.set_ydata(power_percents)
        fig.canvas.draw_idle()

    # register the update function with each slider
    slider_p.on_changed(update)
    slider_i.on_changed(update)
    slider_d.on_changed(update)

    plt.show()


if __name__ == "__main__":
    main()
