RingBuffer
==========
Simple ring/circular buffer for storing numbers.
Commonly used for moving-window statistics.

Dependencies
^^^^^^^^^^^^

No dependencies.

RingBuffer
^^^^^^^^^^
Demo code showing off most of RingBuffer's functionality:

.. code-block:: python

   from ringbuffer import RingBuffer

   buf = RingBuffer(3)

   len(buf)  # 0, there are 0 elements currently in the RingBuffer
   buf.max_size  # 3, The RingBuffer can hold up to 3 elements.

   buf.append(5)
   buf.append(10)
   buf.append(25)

   # Common statistics
   buf.mean()  #  13.3333
   buf.median()  # 10.0
   buf.min()  # 5.0
   buf.max()  # 25.0

   # Finite Differences
   # ``buf.diff()`` returns a generator.
   list(buf.diff())  # [5.0, 15.0],  Will be 1-shorter than ``len(buf)``.

   # Indexing
   buf.append(50)  # Will overwrite the first element, that used to be ``5``
   buf[0]  # 10.0, the 0th index will contain the oldest value
   buf[-1]  # 50.0, the -1th index will contain the newest value

   buf.full  # True, the buffer is currently full

   list(
       buf
   )  # [10.0, 25.0, 50.0], iterating over RingBuffer will go from oldest to newest.

   buf.clear()  # Resets the RingBuffer
   buf.full  # False, the RingBuffer has been cleared and is currently empty.


The underlying element size can be configured by specifying the ``dtype`` argument:

.. code-block:: python

   buf = RingBuffer(3, "b")  # signed character
   buf = RingBuffer(3, dtype="d")  # double

All ``dtype`` specifiers are the same as for ``array.array`` objects.

+-------+--------------------+------+
| dtype | C Type             | Size |
+=======+====================+======+
| ``b`` | signed char        | 1    |
+-------+--------------------+------+
| ``B`` | unsigned char      | 1    |
+-------+--------------------+------+
| ``h`` | signed short       | 2    |
+-------+--------------------+------+
| ``H`` | unsigned short     | 2    |
+-------+--------------------+------+
| ``i`` | signed int         | 2    |
+-------+--------------------+------+
| ``I`` | unsigned int       | 2    |
+-------+--------------------+------+
| ``l`` | signed long        | 4    |
+-------+--------------------+------+
| ``L`` | unsigned long      | 4    |
+-------+--------------------+------+
| ``q`` | signed long long   | 8    |
+-------+--------------------+------+
| ``Q`` | unsigned long long | 8    |
+-------+--------------------+------+
| ``f`` | float (DEFAULT)    | 4    |
+-------+--------------------+------+
| ``d`` | double             | 8    |
+-------+--------------------+------+
