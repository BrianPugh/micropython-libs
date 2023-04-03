lzss
====
LZSS is a compression library.

Not all files in this module are required:

* `lzss/__init__.py` - Always required.

* `lzss/compressor_viper.py` - Viper-optimized compressor. Recommended for on-device compression.

* `lzss/compressor.py` - CPython-compatible compressor.

* `lzss/decompressor_viper.py` - Viper-optimized decompressor. Currently not implemented.

* `lzss/decompressor.py` - CPython-compatible decompressor.


Dependencies
^^^^^^^^^^^^

No dependencies.

Compressor
^^^^^^^^^^
Compresses data to an output stream.

Primary configuration values:

* ``window_bits`` - Defaults to 10 (1KB window).

* ``size_bits`` - Maximum pattern length. Defaults to 4 (which equates to ~18 bytes).

* ``literal_bits`` - Number of actual bits in each input byte. Defaults to 8.

.. code-block:: python

    from io import BytesIO
    from lzss import Compressor, Decompressor

    with BytesIO() as f:
        compressor = Compressor(f, literal_bits=7)
        compressor.compress(b"battery: 97%; sensor: 2.65v\n")
        compressor.compress(b"battery: 97%; sensor: 2.68v\n")
        compressor.compress(b"battery: 96%; sensor: 2.63v\n")
        compressor.compress(b"battery: 96%; sensor: 2.61v\n")
        compressor.compress(b"battery: 96%; sensor: 2.63v\n")
        compressor.flush()
        print(f"Compressed length: {f.tell()}")
        f.seek(0)
        decompressor = Decompressor(f)
        out = decompressor.decompress()
        print(f"Decoded length: {len(out)}")
        print(f"Decoded:\n{out.decode()}")

results in:

.. code-block:: bash

   Compressed length: 54
   Decoded length: 140
   Decoded:
   battery: 97%; sensor: 2.65v
   battery: 97%; sensor: 2.68v
   battery: 96%; sensor: 2.63v
   battery: 96%; sensor: 2.61v
   battery: 96%; sensor: 2.63v

Decompressor
^^^^^^^^^^^^
The ``Decompressor`` object reads the compression settings from the compression header written by the ``Compressor``.

Implementation Details
^^^^^^^^^^^^^^^^^^^^^^
