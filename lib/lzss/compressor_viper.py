import time

import micropython

t_search = 0

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

        self.min_pattern_len = _compute_min_pattern_bytes(
            self.window_bits, self.size_bits
        )
        self.max_pattern_len = (
            1 << self.size_bits
        ) + self.min_pattern_len - 1

        self._bit_writer = BitWriter(f)

        self.buffer = bytearray(2 ** self.window_bits)
        self.buffer_pos = 0

        # Write header
        self._bit_writer.write(window_bits - 8, 3)
        self._bit_writer.write(size_bits - 4, 2)
        self._bit_writer.write(literal_bits - 5, 2)
        self._bit_writer.write(0, 1)  # No other header bytes

    @micropython.viper
    def compress(self, data_bytes):
        self.buffer_pos = self._compress(data_bytes)

    @micropython.viper
    def _compress(self, data_bytes) -> int:
        t_search = int(0)
        data_len = int(len(data_bytes))
        data = ptr8(data_bytes)

        buffer = ptr8(self.buffer)
        buffer_len = int(len(self.buffer))
        buffer_pos = int(self.buffer_pos)

        min_pattern_len = int(self.min_pattern_len)
        max_pattern_len = int(self.max_pattern_len)
        size_bits = int(self.size_bits)

        data_pos = int(0)
        while data_pos < data_len:
            # Find longest pattern match
            best_buffer_pos = int(0)
            best_pattern_len = int(0)
            t_search_start = time.ticks_us()
            for buffer_search_start in range(buffer_len - min_pattern_len + 1):
                if buffer[buffer_search_start] != data[data_pos]:
                    # Execution shortcut; first symbol usually doesn't match.
                    continue

                if buffer[buffer_search_start+1] != data[data_pos+1]:
                    # Execution shortcut; a pattern doesn't exist.
                    continue

                for pattern_len in range(2, max_pattern_len):
                    buffer_search_pos = buffer_search_start + pattern_len
                    data_search_pos = data_pos + pattern_len

                    # Don't check bounds here, this loop is too tight.
                    if buffer[buffer_search_pos] != data[data_search_pos]:
                        break
                else:
                    best_buffer_pos = buffer_search_start
                    best_pattern_len = max_pattern_len
                    break

                if pattern_len > best_pattern_len:
                    if buffer_search_pos >= buffer_len:
                        # Bounds check here; gets executed less often
                        break
                    best_buffer_pos = buffer_search_start
                    best_pattern_len = pattern_len
            t_search += int(time.ticks_diff(time.ticks_us(), t_search_start))

            if best_pattern_len >= min_pattern_len:
                self._bit_writer.write(
                    (best_buffer_pos << size_bits)
                    | (best_pattern_len - min_pattern_len),
                    self.token_bits,
                )
                # Copy pattern into buffer
                for j in range(best_pattern_len):
                    buffer[buffer_pos] = data[data_pos + j]
                    buffer_pos = (buffer_pos + 1) % buffer_len
                data_pos += best_pattern_len
            else:
                self._bit_writer.write(data[data_pos] | 0x100, 9)
                buffer[buffer_pos] = data[data_pos]
                buffer_pos = (buffer_pos + 1) % buffer_len
                data_pos += 1
        print(f"t_search: {t_search}us")
        return buffer_pos

    def flush(self):
        self._bit_writer.flush()
