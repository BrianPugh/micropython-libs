OverSample
==========

Dependencies
^^^^^^^^^^^^

No dependencies


Oversample
^^^^^^^^^^
OOP oversampling of a callable function.

.. code-block:: python

   from oversample import Oversample


   def foo():  # takes no arguments
       return 42


   oversample_foo = Oversample(foo, 64)  # Will sample foo 64 times each call
   oversampled_value = oversample_foo()


oversample
^^^^^^^^^^
Functional oversampling a callable function.

.. code-block:: python

   from oversample import oversample


   def foo():  # takes no arguments
       return 42


   oversampled_value = oversample(foo, 64)  # Sample foo 64 times
