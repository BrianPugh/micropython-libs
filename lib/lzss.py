"""Modified LZSS encoding for efficient micropython.

Token encoding:

* Each token is 16 bits (2 bytes)
* 12 bits window
* 4 bits length
* actual length is length + 3 since tokens <=2 are not encoded;
  so actual lengths will be in range [3, 18].
* a 1 byte flag bitfield will represent the type of the next 8 references/literals.

Compromises:
    * if a string occurs at the ringbuffer wraparound point, it won't be detected.
      This results in slightly lower compression ratios for faster operation and
      smaller/simpler implementation.
"""
from math import ceil

WINDOW_BITS = 10
SIZE_BITS = 4
MIN_PATTERN_BYTES = ceil((WINDOW_BITS + SIZE_BITS) / 9 + 0.001)

# w=13, s=4
# 1 literal takes up 9 bits; 1 token takes up 18 bits
# 2 literal takes up 18 bits; 1 token takes up 18 bits

# w=11, s=4
# 1 literal takes up 9 bits; 1 token takes up 16 bits
# 2 literal takes up 18 bits; 1 token takes up 16 bits

# w=10, s=4
# 1 literal takes up 9 bits; 1 token takes up 15 bits
# 2 literal takes up 18 bits; 1 token takes up 15 bits

# w=8, s=4
# 1 literal takes up 9 bits; 1 token takes up 12 bits
# 2 literal takes up 18 bits; 1 token takes up 12 bits


BUFFER_BYTES = 2**WINDOW_BITS
MAX_PATTERN_SIZE = SIZE_BITS**2 + MIN_PATTERN_BYTES


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


class Compressor:
    def __init__(self, f):
        self._bit_writer = BitWriter(f)
        self.ring_buffer = RingBuffer(BUFFER_BYTES)

    def compress(self, data):
        data_start = 0
        while data_start < len(data):
            search_i = 0
            match_size = 1
            for size in range(MIN_PATTERN_BYTES, MAX_PATTERN_SIZE):
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
                self._bit_writer.write(search_i, WINDOW_BITS)
                self._bit_writer.write(match_size - MIN_PATTERN_BYTES, SIZE_BITS)

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
        self.ring_buffer = RingBuffer(BUFFER_BYTES)
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
                    index = self._bit_reader.read(WINDOW_BITS)
                    match_size = self._bit_reader.read(SIZE_BITS) + MIN_PATTERN_BYTES

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
