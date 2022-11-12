import argparse
from pathlib import Path

import belay

parser = argparse.ArgumentParser()
parser.add_argument("port")
args = parser.parse_args()

device = belay.Device(args.port)
device.sync(Path(__file__).parent.parent / "lib" / "max6675.py")
device.sync(Path(__file__).parent.parent / "lib" / "controlhal.py")


@device.task
def temperature_loop():
    from max6675 import Max6675, OpenThermocouple

    spi = SPI(0, mosi=Pin(3, Pin.OUT), miso=Pin(4), sck=Pin(2, Pin.OUT))
    temperature_sensor = Max6675(spi, Pin(5, Pin.OUT))
    while True:
        try:
            print(temperature_sensor())
        except OpenThermocouple:
            print("OPEN")
        time.sleep(0.25)


temperature_loop()
