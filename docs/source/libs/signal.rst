Signal
======

Python reimplementation of ``machine.Signal``.

The builtin ``machine.Signal`` class doesn't handle pin-like objects well.
However, this implementation won't be as fast/resource-efficient,
but that's fine for many cases.

If wrapping a vanilla ``machine.Pin`` object, it's recommended to use the
built in ``machine.Signal`` class. If wrapping an object that implements the pin Protocol, then use the ``Signal`` class implemented here.


Dependencies
^^^^^^^^^^^^

No dependencies

Signal
^^^^^^

The ``Signal`` class takes in a Pin-like object as input.
Optionally, set the ``invert=True`` flag to invert physical
input/output values.

.. code-block:: python

   from debouncedpin import DebouncedPin
   from signal import Signal

   pin = DebouncedPin(7)  # This won't work with ``machine.Signal``
   signal = Signal(pin, invert=True)  # If the output is active-low

   signal.on()  # Turn signal off, setting pin high
   signal.off()  # Turn signal off, setting pin low
   signal.value(True)  # alternative ways to turn signal on
   signal(True)

   val = signal()  # Read input; this also abides by ``invert``.
   val = signal.value()


   def foo():  # takes no arguments
       return 42


   oversample_foo = Oversample(foo, 64)  # Will sample foo 64 times each call
   oversampled_value = oversample_foo()
