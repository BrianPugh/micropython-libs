import max6675
import pytest


def test_prev_baudrate():
    class SPI:
        def __repr__(self):
            return "SPI(0, baudrate=992063, polarity=0, phase=0, bits=8, sck=6, mosi=7, miso=4)"

    spi = SPI()
    actual = max6675._prev_baudrate(spi)
    assert actual == 992_063


def test_interpret_buf():
    data = bytearray([0b0111_1111, 0b1111_1000])
    assert 1023.75 == max6675._interpret_buf(data)


def test_interpret_buf_open_thermocouple():
    data = bytearray([0b0111_1111, 0b1111_1100])
    with pytest.raises(max6675.OpenThermocouple):
        max6675._interpret_buf(data)


def test_interpret_buf_bad_dummy_bit():
    data = bytearray([0b1111_1111, 0b1111_1000])
    with pytest.raises(RuntimeError):
        max6675._interpret_buf(data)
