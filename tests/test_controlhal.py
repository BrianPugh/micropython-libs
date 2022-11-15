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


@pytest.fixture
def sensor(mocker):
    class TestSensor(Sensor):
        _raw_read = mocker.MagicMock(return_value=7)

    return TestSensor()


@pytest.fixture
def actuator(mocker):
    class TestActuator(Actuator):
        _raw_write = mocker.MagicMock()

    return TestActuator()


@pytest.fixture
def controller(mocker):
    return mocker.MagicMock(return_value=0.123)


@pytest.fixture
def mock_pidautotune(mocker):
    return mocker.patch("controlhal.PIDAutotune")


def test_control_loop_basic(mocker, sensor, actuator, controller):
    controller2 = mocker.MagicMock(return_value=0.456)
    control_loop = ControlLoop(actuator, sensor, controller)
    control_loop()
    actuator._raw_write.assert_called_once()
    sensor._raw_read.assert_called_once()
    controller.assert_called_once()

    with control_loop.use(controller2):
        assert control_loop._controllers == [controller, controller2]
        control_loop()
        controller2.assert_called_once()

    assert control_loop._controllers == [controller]


def test_control_loop_eq(actuator, sensor, controller):
    control_loop1 = ControlLoop(actuator, sensor, controller)
    control_loop2 = ControlLoop(actuator, sensor, controller)

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
