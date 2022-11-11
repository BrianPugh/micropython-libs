import argparse
from pathlib import Path

import belay

lib = Path(__file__).parent.parent / "lib" / "debouncedpin.py"

parser = argparse.ArgumentParser()
parser.add_argument("port")
parser.add_argument("--pin", type=int, default=14)
parser.add_argument("--debounce", action="store_true")
parser.add_argument("--debounce-led", action="store_true")
args = parser.parse_args()

device = belay.Device(args.port)
device.sync(lib)


@device.task
def normal(pin):
    """Non-debounced switch.

    The counter should (maybe) increment multiple times whenever you press the button.
    """
    count = 0
    button = Pin(pin, Pin.IN, Pin.PULL_UP)

    def handler(pin):
        nonlocal count
        count += 1
        print(count)

    button.irq(handler=handler, trigger=Pin.IRQ_FALLING)
    while True:
        time.sleep(1)


@device.task
def debounced(pin):
    from debouncedpin import DebouncedPin

    count = 0

    def handler(pin):
        nonlocal count
        count += 1
        print(count)

    pin = DebouncedPin(pin, Pin.PULL_UP)
    pin.irq(handler, DebouncedPin.IRQ_FALLING)

    while True:
        time.sleep(1)


@device.task
def debounced_led(pin):
    from debouncedpin import DebouncedLedPin

    count = 0

    def handler(pin):
        nonlocal count
        count += 1
        if count % 2:
            pin.on()
        else:
            pin.off()
        print(count)

    pin = DebouncedLedPin(pin, Pin.PULL_UP)
    pin.irq(handler, DebouncedLedPin.IRQ_FALLING)

    while True:
        time.sleep(1)


if args.debounce_led:
    debounced_led(args.pin)
elif args.debounce:
    debounced(args.pin)
else:
    normal(args.pin)
