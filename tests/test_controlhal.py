import pytest
from common import MockTime
from controlhal import (
    Actuator,
    ControlLoop,
    Derivative,
    Peripheral,
    Sensor,
    TimeProportionalActuator,
)


@pytest.fixture
def mock_time(mocker):
    return MockTime.patch(mocker, "controlhal.time_ms")


def test_peripheral_default_period():
    peripheral = Peripheral()
    assert peripheral.period == 0.01


def test_peripheral_invalid_period():
    with pytest.raises(ValueError):
        Peripheral(period=0)

    with pytest.raises(ValueError):
        Peripheral(period=-0.1)


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

    sensor = TestSensor(period=0.01)
    derivative = Derivative(sensor)

    # First 4 reads should return no derivative while
    # the buffer fills.
    assert 0 == derivative.read()
    assert len(derivative._val_buffer) == 1
    assert (
        0 == derivative.read()
    )  # Second read at same time should not increase buffer.
    assert len(derivative._val_buffer) == 1
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


def test_control_loop_from_tuple(mock_pid, sensor, actuator):
    control_loop = ControlLoop(actuator, sensor)

    mock_pid.assert_called_once_with(1.0, 0.0, 0.0, output_limits=(0, 1), period=0.01)
    control_loop.pid.set_auto_mode.assert_called_once_with(True)
    assert control_loop.tunings == control_loop.pid.tunings
    assert control_loop.compute_tunings() == control_loop.tunings

    control_loop.pid.side_effect = lambda x: 0.7

    assert control_loop.read() == 7
    control_loop.write(17)
    assert control_loop.setpoint == 17

    control_loop()
    actuator._raw_write.assert_called_once_with(0.7)


def test_control_loop_from_pid(mocker, mock_pid, sensor, actuator):
    pid = mocker.MagicMock()
    ControlLoop(actuator, sensor, pid=pid)
    pid.set_auto_mode.assert_called_once()
    mock_pid.assert_not_called()


def test_control_loop_autotune(mock_pid, mock_pidautotune, sensor, actuator):
    control_loop = ControlLoop(actuator, sensor)
    control_loop.pid.set_auto_mode.assert_called_once_with(True)

    control_loop.set_mode_autotune(100)
    mock_pidautotune.assert_called_once()
    control_loop.pid.set_auto_mode.assert_called_with(False)

    # Since we are already in autotune mode;
    # subsequent calls shouldn't do anything.
    control_loop.set_mode_autotune(100)
    mock_pidautotune.assert_called_once()

    control_loop.autotuner.side_effect = lambda x: 0.7

    control_loop()
    actuator._raw_write.assert_called_once_with(0.7)

    control_loop.compute_tunings()
    control_loop.autotuner.compute_tunings.assert_called_once()


def test_control_loop_autotune_impossible_state(
    mock_pid, mock_pidautotune, sensor, actuator
):
    control_loop = ControlLoop(actuator, sensor)
    control_loop.mode = ControlLoop.MODE_AUTOTUNE
    with pytest.raises(Exception):
        control_loop()
    with pytest.raises(Exception):
        control_loop.compute_tunings()


def test_control_loop_eq(actuator, sensor):
    control_loop1 = ControlLoop(actuator, sensor)
    control_loop2 = ControlLoop(actuator, sensor)

    assert control_loop1 == control_loop2
    assert control_loop1 != 4


@pytest.fixture
def mock_timer(mocker):
    return mocker.patch("controlhal.Timer")


def test_time_proportional_actuator_basic(mocker, mock_timer, mock_time):
    pin = mocker.MagicMock()

    actuator = TimeProportionalActuator(pin=pin, period=10)
    mock_timer.assert_called_once_with(-1)
    # configure timer to execute callback once every 10mS
    actuator._timer.init.assert_called_once_with(
        period=100, callback=actuator._timer_callback
    )

    pin.assert_not_called()
    actuator.write(0.7)
    # Pin won't be activated yet; it gets activated on counter tick.
    pin.assert_not_called()

    for t_ms in range(20_000):
        mock_time.time = t_ms
        if t_ms % 100 == 0:
            actuator._timer_callback(actuator._timer)

        if t_ms == 0 or t_ms == 6_999:
            pin.assert_called_once_with(1)
        if t_ms == 7_000 or t_ms == 9_999:
            assert len(pin.call_args_list) == 2
            assert pin.call_args_list[-1] == mocker.call(0)
        if t_ms == 10_000 or t_ms == 16_999:
            assert len(pin.call_args_list) == 3
            assert pin.call_args_list[-1] == mocker.call(1)
        if t_ms == 17_000 or t_ms == 19_999:
            assert len(pin.call_args_list) == 4
            assert pin.call_args_list[-1] == mocker.call(0)


def test_time_proportional_actuator_change(mocker, mock_timer, mock_time):
    pin = mocker.MagicMock()

    actuator = TimeProportionalActuator(pin=pin, period=10)
    mock_timer.assert_called_once_with(-1)
    # configure timer to execute callback once every 10mS
    actuator._timer.init.assert_called_once_with(
        period=100, callback=actuator._timer_callback
    )

    pin.assert_not_called()
    actuator.write(0.7)
    pin.assert_not_called()

    for t_ms in range(20_000):
        mock_time.time = t_ms

        if t_ms == 300:
            actuator.write(0.6)

        if t_ms % 100 == 0:
            actuator._timer_callback(actuator._timer)

        if t_ms == 0 or t_ms == 5_999:
            pin.assert_called_once_with(1)
        if t_ms == 6_000 or t_ms == 9_999:
            assert len(pin.call_args_list) == 2
            assert pin.call_args_list[-1] == mocker.call(0)
        if t_ms == 10_000 or t_ms == 15_999:
            assert len(pin.call_args_list) == 3
            assert pin.call_args_list[-1] == mocker.call(1)
        if t_ms == 16_000 or t_ms == 19_999:
            assert len(pin.call_args_list) == 4
            assert pin.call_args_list[-1] == mocker.call(0)
