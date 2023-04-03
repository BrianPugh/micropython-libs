lzss
====
LZSS is a compression library.

Not all files in this module are required:

* ``lzss/__init__.py`` - Always required.

* ``lzss/compressor_viper.py`` - Viper-optimized compressor. Recommended for on-device compression.

* ``lzss/compressor.py`` - CPython-compatible compressor.

* ``lzss/decompressor_viper.py`` - Viper-optimized decompressor. Currently not implemented.

* ``lzss/decompressor.py`` - CPython-compatible decompressor.


Dependencies
^^^^^^^^^^^^

No dependencies.

Compressor
^^^^^^^^^^
Compresses data to an output stream.

Primary configuration values:

* ``window`` - Number of window bits. Defaults to 10 (1KB window).

* ``size`` - Maximum pattern length. Defaults to 4 (which equates to ~18 bytes).

* ``literal`` - Number of actual bits in each input byte. Defaults to 8.

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
The ``Decompressor.decompress`` method takes an optional argument ``size``. If provided, up to ``size`` bytes will
be decoded. If less than ``size`` bytes are returned, then the end of stream has been reached.

Implementation Details
^^^^^^^^^^^^^^^^^^^^^^

Stream Header
~~~~~~~~~~~~~
The Bit location is given via the syntax ``byte[bit]``.
The locations are zero index.
For example, ``1[7]`` would be the most significant bit of the second byte of the stream.

+----------+--------------+------------------------------------------------------------------------+
| Bits     | Name         | Description                                                            |
+==========+==============+========================================================================+
| 0[7,6,5] | window       | Number of bits, minus 8, used to represent the size                    |
|          |              | of the shifting window.                                                |
|          |              | e.g. A 12-bit window is encoded as the number 4, 0b100.                |
|          |              | This means the smallest window is 256 bytes, and largest is 32768.     |
+----------+--------------+------------------------------------------------------------------------+
| 0[4,3]   | pattern_size | Number of bits, minus ``min_pattern_len``, used to encode the length   |
|          |              | of a pattern match. The min_pattern_len is determined by a combination |
|          |              | of these parameters.                                                   |
|          |              | For example, a 4-bit size with a 12-bit window results in a            |
|          |              | ``min_pattern_len`` of 3, so 4-bits can represent the lengths 3~18.    |
+----------+--------------+------------------------------------------------------------------------+
| 0[2,1]   | literal_size | Number of bits, minus 5, in a literal.                                 |
|          |              | For example, 0b11 represents a standard 8 bit (1 byte) literal.        |
+----------+--------------+------------------------------------------------------------------------+
| 0[0]     | more_header  | If ``True``, then the next byte in the stream is more header data.     |
|          |              | Currently always ``False``, but allows for future expandability.       |
+----------+--------------+------------------------------------------------------------------------+

Stream Encoding/Decoding
~~~~~~~~~~~~~~~~~~~~~~~~
After the header bytes is the data stream. The datastream is written in bits, so all data is packed
tightly with no padding.

Explaining the stream is easiest in the view of decoding instructions:

1. Read 1 bit, representing the ``is_literal`` flag.

2. If ``is_literal`` is ``True``, then the next ``literal_size`` bits represent the next output character.

3. If ``is_literal`` if then:

   a. Read ``window`` bits. This represents the offset from the beginning of the buffer to the pattern occurrence.

   b. Read ``pattern_size`` bits. After arithmetic, this represents the number of characters to copy from the buffer.

For compressing data, the reverse process is performed. Try and greedily match the longest input stream in the
moving-window-buffer. If the pattern match is shorter than ``min_pattern_len``, then output a literal.
