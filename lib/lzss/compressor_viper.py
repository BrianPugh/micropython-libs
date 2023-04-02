import micropython

from .common import RingBuffer


class BitWriter:
    """Writes bits to a stream."""

    def __init__(self, f):
        self.f = f
        self.buffer = 0  # Basically a uint24
        self.bit_pos = 0

    def write(self, bits, num_bits):
        self.bit_pos += num_bits
        self.buffer |= bits << (32 - self.bit_pos)

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


def _compute_min_pattern_bytes(window_bits, size_bits):
    return int((window_bits + size_bits) / 9 + 1.001)


class Compressor:
    def __init__(self, f, window_bits=10, size_bits=4, literal_bits=8):
        self.window_bits = window_bits
        self.size_bits = size_bits
        self.literal_bits = literal_bits

        if literal_bits != 8:
            raise NotImplementedError

        self.token_bits = window_bits + size_bits + 1

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
        self._bit_writer.write(literal_bits - 5, 2)
        self._bit_writer.write(0, 1)  # No other header bytes

    def compress(self, data):
        data_start = 0

        # Primary compression loop.
        while data_start < len(data):
            search_i = 0
            for match_size in range(
                self.min_pattern_bytes, self.max_pattern_bytes_exclusive
            ):
                data_end = data_start + match_size
                if data_end > len(data):
                    match_size = match_size - 1
                    break
                string = data[data_start:data_end]
                try:
                    search_i = self.ring_buffer.index(string, search_i)  # ~14% of time
                except ValueError:
                    match_size = match_size - 1
                    string = string[:-1]
                    break  # Not Found

            if match_size >= self.min_pattern_bytes:
                self._bit_writer.write(
                    (search_i << self.size_bits)
                    | (match_size - self.min_pattern_bytes),
                    self.token_bits,
                )
                self.ring_buffer.write_bytes(string)
                data_start += match_size
            else:
                self._bit_writer.write(data[data_start] | 0x100, 9)
                self.ring_buffer.write_byte(data[data_start])
                data_start += 1

    def flush(self):
        self._bit_writer.flush()
