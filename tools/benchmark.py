"""Answers the question "how slow is XYZ?".

Was used to determine if Oversample-conversion optimizations
were worth additional API complexity.

+--------------+---------+---------+---------+-------------+-------------+
| Device       | FLOPS   | ADC     | ADC-Add | ADC-Add-Div | GPIO-Toggle |
+==============+=========+=========+=========+=============+=============+
| rp2040       | 131,257 | 138,091 | 46,362  | 47,160      | 227,841     |
+--------------+---------+---------+---------+-------------+-------------+
"""
import argparse
from pathlib import Path

import belay

parser = argparse.ArgumentParser()
parser.add_argument("port")
parser.add_argument("--flops", action="store_true")
parser.add_argument("--adc", action="store_true")
parser.add_argument("--adc-add", action="store_true")
parser.add_argument("--adc-add-div", action="store_true")
parser.add_argument("--gpio-toggle", action="store_true")
args = parser.parse_args()

device = belay.Device(args.port)


@device.task()
def flops():
    import time

    t_start = time.ticks_us()
    for i in range(100_000):
        # Loop unrolling for a bit more accuracy
        res = i * 1.1
        res = i * 2.1
        res = i * 3.1
        res = i * 4.1
        res = i * 5.1
        res = i * 6.1
        res = i * 7.1
        res = i * 8.1
        res = i * 9.1
        res = i * 10.1  # noqa: F841

    t_end = time.ticks_us()
    t_diff = time.ticks_diff(t_end, t_start)
    t_diff /= 1_000_000
    return 1_000_000 / t_diff


@device.task
def adc():
    import time

    from machine import ADC

    t_start = time.ticks_us()

    adc = ADC(4)
    for _ in range(100_000):
        adc.read_u16()
        adc.read_u16()
        adc.read_u16()
        adc.read_u16()
        adc.read_u16()
        adc.read_u16()
        adc.read_u16()
        adc.read_u16()
        adc.read_u16()
        adc.read_u16()
    t_end = time.ticks_us()
    t_diff = time.ticks_diff(t_end, t_start)
    t_diff /= 1_000_000
    return 1_000_000 / t_diff


@device.task
def adc_add():
    import time

    from machine import ADC

    t_start = time.ticks_us()

    adc = ADC(4)
    res = 0
    for _ in range(100_000):
        res += adc.read_u16()
        res += adc.read_u16()
        res += adc.read_u16()
        res += adc.read_u16()
        res += adc.read_u16()
        res += adc.read_u16()
        res += adc.read_u16()
        res += adc.read_u16()
        res += adc.read_u16()
        res += adc.read_u16()
    t_end = time.ticks_us()
    t_diff = time.ticks_diff(t_end, t_start)
    t_diff /= 1_000_000
    return 1_000_000 / t_diff


@device.task
def adc_add_div():
    import time

    from machine import ADC

    t_start = time.ticks_us()

    adc = ADC(4)
    res = 0
    for _ in range(100_000):
        res += adc.read_u16() / 2.1
        res += adc.read_u16() / 2.1
        res += adc.read_u16() / 2.1
        res += adc.read_u16() / 2.1
        res += adc.read_u16() / 2.1
        res += adc.read_u16() / 2.1
        res += adc.read_u16() / 2.1
        res += adc.read_u16() / 2.1
        res += adc.read_u16() / 2.1
        res += adc.read_u16() / 2.1
    t_end = time.ticks_us()
    t_diff = time.ticks_diff(t_end, t_start)
    t_diff /= 1_000_000
    return 1_000_000 / t_diff


@device.task
def gpio_toggle():
    import time

    t_start = time.ticks_us()

    pin = Pin(25, Pin.OUT)
    for _ in range(100_000):
        pin.on()
        pin.off()
        pin.on()
        pin.off()
        pin.on()
        pin.off()
        pin.on()
        pin.off()
        pin.on()
        pin.off()

    t_end = time.ticks_us()
    t_diff = time.ticks_diff(t_end, t_start)
    t_diff /= 1_000_000
    return 1_000_000 / t_diff


if args.flops:
    print(f"{flops():,} FLOPS.")
if args.adc:
    print(f"{adc():,} ADC conversions per second.")
if args.adc_add:
    print(f"{adc_add():,} ADC-Adds per second.")
if args.adc_add_div:
    print(f"{adc_add_div():,} ADC-Add-Divs per second.")
if args.gpio_toggle:
    print(f"{gpio_toggle():,} GPIO toggles per second.")
