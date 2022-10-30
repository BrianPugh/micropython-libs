import math
from collections import deque


class WaterTank:
    # specific heat capacity of water: c = 4.182 kJ / kg * K
    SPECIFIC_HEAT_CAP_WATER = 4.182

    # thermal conductivity of steel: lambda = 15 W / m * K
    THERMAL_CONDUCTIVITY_STEEL = 15

    def __init__(self, diameter=2.5, volume=0.1, temp=20.0, density=1.0, delay=100):
        """Simulate a water tank.

        Adapted from:
            https://github.com/hirschmann/pid-autotune/blob/master/kettle.py

        Parameters
        ----------
        diameter: float
            WaterTank diameter in centimeters.
        volume: float
            Content volume in liters.
        temp: float
            Initial content temperature in degree celsius.
        density: float
            Content density.
        """
        self._delay_buffer = deque()
        self._delay = delay
        self._delay_temp = temp
        self._mass = volume * density
        self._temp = temp
        self._initial_temp = temp
        radius = diameter / 2

        # height in cm
        height = (volume * 1000) / (math.pi * math.pow(radius, 2))

        # surface in m^2
        self._surface = (
            2 * math.pi * math.pow(radius, 2) + 2 * math.pi * radius * height
        ) / 10000

    @property
    def temperature(self):
        """Get the content's temperature."""
        return self._temp

    @property
    def delayed_temperature(self):
        return self._delay_temp

    def _heat(self, power, duration, efficiency=0.98):
        """Heat the boiler's content.

        Parameters
        ----------
        power: float
            Power in kW.
        duration: float
            Duration in seconds.
        efficiency: float
            Efficiency as number between 0 and 1.
        """
        self._temp += self._get_deltaT(power * efficiency, duration)

    def _cool(self, duration, ambient_temp=20, heat_loss_factor=1):
        """Make the content loose heat.

        Parameters
        ----------
        duration: float
            Duration in seconds.
        ambient_temp: float
            Ambient temperature in degree celsius.
        heat_loss_factor: float
            Increase or decrease the heat loss by a specified factor.
        """
        # Q = k_w * A * (T_boiler - T_ambient)
        # P = Q / t
        power = (
            self.THERMAL_CONDUCTIVITY_STEEL
            * self._surface
            * (self._temp - ambient_temp)
        )

        # W to kW
        power /= 1000
        self._temp -= self._get_deltaT(power, duration) * heat_loss_factor

    def heat_cool(self, power, duration, heat_loss_factor=1):
        self._heat(power, duration)
        self._cool(duration, heat_loss_factor=heat_loss_factor)
        self._delay_buffer.append(self._temp)
        if len(self._delay_buffer) > self._delay:
            self._delay_temp = self._delay_buffer.popleft()

        return self._delay_temp

    def _get_deltaT(self, power, duration):
        return (power * duration) / (self.SPECIFIC_HEAT_CAP_WATER * self._mass)
