from random import random

import pytest
from oversample import Oversample, oversample


def sensor():
    return 10 + random()


def test_oversample_functional():
    val = oversample(sensor, 1024)
    assert pytest.approx(10, 0.1) == val


def test_oversample_class():
    oversampled_sensor = Oversample(sensor, 1024)
    val = oversampled_sensor()
    assert pytest.approx(10, 0.1) == val
