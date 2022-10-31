import pytest
from common import MockTime
from controlhal import Actuator, ControlLoop, Derivative, Sensor


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


def test_derivative(mock_time):
    class TestSensor(Sensor):
        n_raw_read = 0

        def _raw_read(self):
            self.n_raw_read += 1
            return self.n_raw_read

    sensor = TestSensor(period=0.1)
    derivative = Derivative(sensor)

    # First 4 reads should return no derivative while
    # the buffer fills.
    assert 0 == derivative.read()
    mock_time.time += 100
    assert 0 == derivative.read()
    mock_time.time += 100
    assert 0 == derivative.read()
    mock_time.time += 100
    assert 0 == derivative.read()
    mock_time.time += 100

    val = derivative.read()
    mock_time.time += 100

    assert derivative._val_buffer == [1.0, 2.0, 3.0, 4.0, 5.0]
    assert derivative._time_buffer == [0.0, 100.0, 200.0, 300.0, 400.0]

    assert val == 10

    val = derivative.read()
    mock_time.time += 100

    assert val == 10


def test_control_loop_invalid_dtype(mocker):
    with pytest.raises(ValueError):
        ControlLoop(1, 2)


@pytest.fixture
def sensor(mocker):
    class TestSensor(Sensor):
        def _raw_read(self):
            return 7

    return TestSensor()


@pytest.fixture
def actuator(mocker):
    class TestActuator(Actuator):
        _raw_write = mocker.MagicMock()

    return TestActuator()


@pytest.fixture
def mock_pid(mocker):
    return mocker.patch("controlhal.PID")


@pytest.fixture
def mock_pidautotune(mocker):
    return mocker.patch("controlhal.PIDAutotune")


def test_control_loop(mock_pid, sensor, actuator):
    control_loop = ControlLoop(actuator, sensor)

    mock_pid.assert_called_once_with(1.0, 0.0, 0.0, output_limits=(0, 1), period=0.01)
    control_loop.pid.set_auto_mode.assert_called_once_with(True)
    assert control_loop.tunings == control_loop.pid.tunings

    control_loop.pid.side_effect = lambda x: 0.7

    assert control_loop.read() == 7
    control_loop.write(17)
    assert control_loop.setpoint == 17

    control_loop()
    actuator._raw_write.assert_called_once_with(0.7)


def test_control_loop_autotune(mock_pid, mock_pidautotune, sensor, actuator):
    control_loop = ControlLoop(actuator, sensor)
    control_loop.pid.set_auto_mode.assert_called_once_with(True)

    control_loop.set_mode_autotune(100)
    control_loop.pid.set_auto_mode.assert_called_with(False)

    control_loop.autotuner.side_effect = lambda x: 0.7

    control_loop()
    actuator._raw_write.assert_called_once_with(0.7)


def test_control_loop_eq(actuator, sensor):
    control_loop1 = ControlLoop(actuator, sensor)
    control_loop2 = ControlLoop(actuator, sensor)

    assert control_loop1 == control_loop2