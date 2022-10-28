import argparse
from pathlib import Path

import belay

lib = Path(__file__).parent.parent / "lib" / "debouncedpin.py"

parser = argparse.ArgumentParser()
parser.add_argument("port")
parser.add_argument("--pin", type=int, default=14)
parser.add_argument("--debounce", action="store_true")
args = parser.parse_args()

device = belay.Device(args.port)
device.sync(lib)


@device.task
def debounced(pin):
    from debouncedpin import DebouncedPin

    count = 0

    def handler(val):
        if not val:
            return
        nonlocal count
        count += 1
        print(count)

    pin = Pin(pin, Pin.IN, Pin.PULL_UP)
    debounced = DebouncedPin(pin, handler)  # noqa: F841

    while True:
        time.sleep(1)


@device.task
def normal(pin):
    count = 0
    button = Pin(pin, Pin.IN, Pin.PULL_UP)

    def handler(pin):
        nonlocal count
        count += 1
        print(count)

    button.irq(handler=handler, trigger=Pin.IRQ_FALLING)
    while True:
        time.sleep(1)


if args.debounce:
    debounced(args.pin)
else:
    normal(args.pin)
