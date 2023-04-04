from . import ExcessBitsError, compute_min_pattern_bytes


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


class RingBuffer:
    def __init__(self, size):
        self.buffer = bytearray(size)
        self.size = size
        self.pos = 0
        self.index = self.buffer.index

    def write_byte(self, byte):  # ~10% of time
        self.buffer[self.pos] = byte
        self.pos = (self.pos + 1) % self.size

    def write_bytes(self, data):
        for byte in data:
            self.write_byte(byte)


class Compressor:
    def __init__(self, f, window=10, size=4, literal=8):
        self.window_bits = window
        self.size_bits = size
        self.literal_bits = literal

        self.token_bits = window + size + 1

        self.min_pattern_bytes = compute_min_pattern_bytes(window, size, literal)
        # up to, not including max_pattern_bytes_exclusive
        self.max_pattern_bytes_exclusive = (
            1 << self.size_bits
        ) + self.min_pattern_bytes

        self._bit_writer = BitWriter(f)
        self.ring_buffer = RingBuffer(2**self.window_bits)

        # Write header
        self._bit_writer.write(window - 8, 3)
        self._bit_writer.write(size - 4, 2)
        self._bit_writer.write(literal - 5, 2)
        self._bit_writer.write(0, 1)  # No other header bytes

    def compress(self, data):
        data_start = 0

        literal_flag = 1 << self.literal_bits
        literal_mask_check = 0xFFFFFFFF - literal_flag + 1

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
                if data[data_start] & literal_mask_check:
                    raise ExcessBitsError

                self._bit_writer.write(
                    data[data_start] | literal_flag, self.literal_bits + 1
                )
                self.ring_buffer.write_byte(data[data_start])
                data_start += 1

    def flush(self):
        self._bit_writer.flush()
