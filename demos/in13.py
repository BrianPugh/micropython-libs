import argparse
from pathlib import Path

import belay

parser = argparse.ArgumentParser()
parser.add_argument("port")
args = parser.parse_args()

device = belay.Device(args.port)
device.sync(Path(__file__).parent.parent / "lib" / "in13.py")


@device.task
def indicator_loop():
    from in13 import IN13

    i2c = I2C(1, sda=Pin(26), scl=Pin(27), freq=400000)
    indicator = IN13(i2c)
    indicator.filter = 1
    while True:
        time.sleep(1.0)
        indicator.value = 0.72
        time.sleep(1.0)
        indicator.value = 0


indicator_loop()
