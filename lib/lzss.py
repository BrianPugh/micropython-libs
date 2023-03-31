"""Modified LZSS encoding for efficient micropython.

The header is a single byte where:
* First 3 bits represent (window_bits minus 8).
  e.g. A 12-bit window is encoded as the number 4, 0b100.
  This means the smallest window is 256 bytes, and largest is 32768.
* The next 2 bits represent (size_bits minus 4).
  e.g. a 4-bit size (max value 19) is encoded as the number 0, 0b00
* Remaining 3 bits are reserved (currently 0b000)


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
from math import ceil


class BitWriter:
    """Writes bits to a stream."""

    def __init__(self, f):
        self.f = f
        self.buffer = 0  # Basically a uint24
        self.bit_pos = 0

    def write(self, bits, num_bits):
        self.buffer |= bits << (32 - self.bit_pos - num_bits)
        self.bit_pos += num_bits

        if self.bit_pos >= 16:
            byte = self.buffer >> 16
            self.f.write(byte.to_bytes(2, "big"))
            self.buffer = (self.buffer & 0xFFFF) << 16
            self.bit_pos -= 16
        elif self.bit_pos >= 8:
            byte = self.buffer >> 24
            self.f.write(byte.to_bytes(1, "big"))
            self.buffer = (self.buffer & 0xFFFFFF) << 8
            self.bit_pos -= 8

    def flush(self):
        if self.bit_pos > 0:
            byte = (self.buffer >> 24) & 0xFF
            self.f.write(byte.to_bytes(1, "big"))
            self.bit_pos = 0


class BitReader:
    """Reads bits from a stream."""

    def __init__(self, f):
        self.f = f
        self.buffer = 0  # Basically a uint32
        self.bit_pos = 0

    def read(self, num_bits):
        while self.bit_pos < num_bits:
            byte = self.f.read(1)
            if not byte:
                raise EOFError
            byte_value = int.from_bytes(byte, "big")
            self.buffer |= byte_value << (24 - self.bit_pos)
            self.bit_pos += 8

        result = self.buffer >> (32 - num_bits)
        mask = (1 << (32 - num_bits)) - 1
        self.buffer = (self.buffer & mask) << num_bits
        self.bit_pos -= num_bits

        return result


class RingBuffer:
    """Simple write-only ring buffer for storing window."""

    def __init__(self, size):
        self.buffer = bytearray(size)
        self.size = size
        self.pos = 0

    def write_byte(self, byte):
        self.buffer[self.pos] = byte
        self.pos = (self.pos + 1) % self.size  # Could use a mask

    def write_bytes(self, data):
        for byte in data:
            self.write_byte(byte)


def _compute_min_pattern_bytes(window_bits, size_bits):
    return ceil((window_bits + size_bits) / 9 + 0.001)


class Compressor:
    def __init__(self, f, window_bits=10, size_bits=4):
        self.window_bits = window_bits
        self.size_bits = size_bits

        self.min_pattern_bytes = _compute_min_pattern_bytes(
            self.window_bits, self.size_bits
        )
        # up to, not including max_pattern_bytes_exclusive
        self.max_pattern_bytes_exclusive = (
            1 << self.size_bits
        ) + self.min_pattern_bytes

        self._bit_writer = BitWriter(f)
        self.ring_buffer = RingBuffer(2**self.window_bits)

        # Write header
        self._bit_writer.write(window_bits - 8, 3)
        self._bit_writer.write(size_bits - 4, 2)
        self._bit_writer.write(0, 3)  # reserved

    def compress(self, data):
        data_start = 0
        while data_start < len(data):
            search_i = 0
            match_size = 1
            for size in range(self.min_pattern_bytes, self.max_pattern_bytes_exclusive):
                data_end = data_start + size
                if data_end > len(data):
                    break
                next_string = data[data_start:data_end]
                try:
                    search_i = self.ring_buffer.buffer.index(
                        next_string, search_i
                    )  # ~28% of time
                except ValueError:
                    break  # Not Found
                string = next_string
                match_size = size

            if match_size > 1:
                self._bit_writer.write(0, 1)  # is token
                self._bit_writer.write(search_i, self.window_bits)
                self._bit_writer.write(
                    match_size - self.min_pattern_bytes, self.size_bits
                )

                self.ring_buffer.write_bytes(string)
            else:
                self._bit_writer.write(1, 1)  # is literal
                self._bit_writer.write(data[data_start], 8)

                self.ring_buffer.write_byte(data[data_start])

            data_start += match_size

    def flush(self):
        self._bit_writer.flush()


class Decompressor:
    def __init__(self, f):
        self._bit_reader = BitReader(f)

        # Read Header
        self.window_bits = self._bit_reader.read(3) + 8
        self.size_bits = self._bit_reader.read(2) + 4
        _ = self._bit_reader.read(3)  # reserved

        # Setup buffers
        self.min_pattern_bytes = _compute_min_pattern_bytes(
            self.window_bits, self.size_bits
        )
        self.ring_buffer = RingBuffer(2**self.window_bits)
        self.overflow = bytearray()

    def decompress(self, size=-1):
        """Returns at most ``size`` bytes."""
        if size < 0:
            size = 0xFFFFFFFF

        if len(self.overflow) > size:
            out = self.overflow[:size]
            self.overflow = self.overflow[size:]
            return out
        elif self.overflow:
            out = self.overflow
            self.overflow = bytearray()
        else:
            out = bytearray()

        while True:
            try:
                is_literal = self._bit_reader.read(1)

                if is_literal:
                    c = self._bit_reader.read(8)
                    self.ring_buffer.write_byte(c)
                    out.append(c)
                else:
                    index = self._bit_reader.read(self.window_bits)
                    match_size = (
                        self._bit_reader.read(self.size_bits) + self.min_pattern_bytes
                    )

                    string = self.ring_buffer.buffer[index : index + match_size]
                    self.ring_buffer.write_bytes(string)

                    if len(out) + len(string) > size:
                        self.overflow = string
                        break
                    else:
                        out.extend(string)
            except EOFError:
                return out

        return out


def main1():
    import time
    from io import BytesIO

    block_size = 1024 * 1024
    uncompressed_len = 0
    expected_uncompressed_len = 100000000
    test_file = "enwik8_1mb"

    t_start = time.time()
    with open("compressed.lzss", "wb") as compressed_f:
        compressor = Compressor(compressed_f)
        with open(test_file, "rb") as f:
            while True:
                # print(f"{100 * uncompressed_len / expected_uncompressed_len:.1f}%")
                data = f.read(block_size)
                if not data:
                    break
                uncompressed_len += len(data)
                compressor.compress(data)
        compressor.flush()
        compressed_len = compressed_f.tell()
    print(f"compressed={compressed_len}")
    print(f"ratio: {uncompressed_len / compressed_len:.3f}")

    with open("compressed.lzss", "rb") as compressed_f:
        decompressor = Decompressor(compressed_f)
        result = decompressor.decompress()

    with open(test_file, "rb") as f:
        test_string = f.read()
    assert len(result) == len(test_string)
    assert result == test_string
    print(f"{len(test_string)=}")

    t_end = time.time()
    t_duration = t_end - t_start
    print(f"{t_duration=}")


def main2():
    from io import BytesIO

    test_string = b"I am sam, sam I am" * 10
    # test_string = b"foo foo"
    with open("compressed.lzss", "wb") as compressed_f:
        compressor = Compressor(compressed_f)
        compressor.compress(test_string)
        compressor.flush()

    with open("compressed.lzss", "rb") as compressed_f:
        decompressor = Decompressor(compressed_f)
        result = decompressor.decompress()
    print(result)


if __name__ == "__main__":
    main1()
