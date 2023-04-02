"""Modified LZSS encoding for efficient micropython.

The header is a single byte where:
* Bits [7,6,5] bits represent (window_bits minus 8).
  e.g. A 12-bit window is encoded as the number 4, 0b100.
  This means the smallest window is 256 bytes, and largest is 32768.
* Bits [4,3] represent (size_bits minus 4).
  e.g. a 4-bit size (max value 19) is encoded as the number 0, 0b00
* Bits [2, 1] represent (literal_length - 5)
    * i.e. 0b11 means that the literal_length is 8bits
* Bit [0] indicates if there is a following header byte (for future upgradability).
  0 means the next byte is **not** a header byte.


Token Encoding
--------------
* Each token is (1 + window_bits + size_bits) bits
* First bit is the ``is_literal`` flag (0 = reference, 1 = literal)

Implementation Details
----------------------
1. The window is kept in a fixed-length ``bytearray``.
   We leverage the builtin ``bytearray.index`` method for efficient pattern search.
2. Because of (1) a string pattern is broken up by the ring buffer wraparound point,
   the pattern won't be detected. This results in potentially slightly lower
   compression ratios for faster operation and smaller/simpler implementation.
"""


class ExcessBitsError(Exception):
    """Provided data has more bits than expected."""


def compute_min_pattern_bytes(window_bits, size_bits, literal_bits):
    return int((window_bits + size_bits) / (literal_bits + 1) + 1.001)


try:
    from .compressor_viper import Compressor
except ImportError:
    try:
        from .compressor import Compressor
    except ImportError:
        pass

try:
    from .decompressor_viper import Decompressor
except ImportError:
    try:
        from .decompressor import Decompressor
    except ImportError:
        pass
