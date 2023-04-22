uProfiler
=========
Tools to help identify slow parts of your code.

Dependencies
^^^^^^^^^^^^

No dependencies


profile
^^^^^^^
The ``profile`` decorator measures how long the function/method takes to execute.

If a ``name`` is not provided, then it is set to the decorated function name.
Decorated functions with the same name will overwrite each other's summary results.

The optional ``print_period`` will control how often the decorator will print
the call timings. Set to 0 to suppress all prints. The **default** global
print period can be configured via ``uprofiler.print_period``.
Defaults to ``1`` (every call).


.. code-block:: python

    from time import sleep
    import uprofiler

    uprofiler.print_period = 1  # Modifies global default


    @uprofiler.profile
    def foo():
        sleep(0.25)


    @uprofiler.profile(name="changed_bar_name")
    def bar():
        sleep(0.6)


    @uprofiler.profile(print_period=3)
    def baz():
        sleep(0.1)


    foo()

    bar()
    bar()

    baz()
    baz()
    baz()

print_results
^^^^^^^^^^^^^
Prints total execution time, as well as a summary of all ``profile`` calls.
``Total-Time`` is computed as the elapsed time between initial ``uprofiler``
import and the ``print_results`` function call.

Place this at the end of your script.

.. code-block:: python

   import uprofiler

   uprofiler.print_results()

The printed output table in this case is empty, since no ``profile`` calls were made.

.. code-block:: text

   Total-Time:  0.983ms
   Name                        Calls    Total (%)     Total (ms)   Average (ms)
   ----------------------------------------------------------------------------

Demo
^^^^
The demo ``demos/uprofiler.py`` prints the following output:

.. code-block:: text

    foo                             1 calls      250.225ms total      250.225ms average
    changed_bar_name                1 calls      600.160ms total      600.160ms average
    changed_bar_name                2 calls     1200.310ms total      600.155ms average
    baz                             3 calls      300.302ms total      100.101ms average
    baz                             6 calls      600.594ms total      100.099ms average

    Total-time: 2184.748ms
    Name                        Calls    Total (%)     Total (ms)   Average (ms)
    ----------------------------------------------------------------------------
    changed_bar_name                2        54.94        1200.31        600.155
    baz                             6        27.49        600.594        100.099
    foo                             1        11.45        250.225        250.225
