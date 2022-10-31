import pytest
from common import MockTime
from controlhal import Actuator, Sensor


@pytest.fixture
def mock_time(mocker):
    return MockTime.patch(mocker, "controlhal.time_ms")


def test_sensor(mock_time):
    class TestSensor(Sensor):
        n_raw_read = 0

        def _raw_read(self):
            self.n_raw_read += 1
            return self.n_raw_read

        def convert(self, x):
            return x / 10

    test_sensor = TestSensor(period=0.1)

    assert 1 == test_sensor.read()
    assert 1 == test_sensor.read()

    mock_time.time = 99  # mS
    assert 1 == test_sensor.read()

    mock_time.time = 100  # mS

    assert 2 == test_sensor.read()
    assert 2 == test_sensor.read()


def test_actuator_invalid_write():
    actuator = Actuator()
    with pytest.raises(ValueError):
        actuator.write(-1)


def test_actuator(mock_time):
    class TestActuator(Actuator):
        n_raw_write = 0

        def _raw_write(self, val):
            self.n_raw_write += val

    test_actuator = TestActuator(period=0.1)

    test_actuator.write(0.5)
    assert test_actuator.n_raw_write == 0.5
    test_actuator.write(0.5)
    assert test_actuator.n_raw_write == 0.5

    mock_time.time = 99  # mS
    test_actuator.write(0.5)
    assert test_actuator.n_raw_write == 0.5

    mock_time.time = 100  # mS

    test_actuator.write(0.5)
    assert test_actuator.n_raw_write == 1
    test_actuator.write(0.5)
    assert test_actuator.n_raw_write == 1
