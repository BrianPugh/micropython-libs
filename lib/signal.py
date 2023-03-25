"""Python reimplementation of ``machine.Signal``.

The builtin ``Signal`` class doesn't handle pin-like objects well.
Won't be as fast/resource-efficient, but that's fine for many cases.
"""


class Signal:
    def __init__(self, pin, invert=False):
        self.pin = pin
        self.invert = invert

    def value(self, x=None):
        if x is None:
            return self.pin() ^ self.invert
        return self.pin(x ^ self.invert)

    def __call__(self, x=None):
        return self.value(x)

    def on(self):
        return self.value(True)

    def off(self):
        return self.value(False)
