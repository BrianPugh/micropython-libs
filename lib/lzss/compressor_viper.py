"""Micropython optimized for performance over readability.
"""
import micropython

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
            self.buffer = 0
        self.f = None  # Prevent future writes


class Compressor:
    def __init__(self, f, window=10, size=4, literal=8):
        self.window_bits = window
        self.size_bits = size
        self.literal_bits = literal

        self.token_bits = window + size + 1

        self.min_pattern_len = compute_min_pattern_bytes(window, size, literal)
        self.max_pattern_len = (1 << self.size_bits) + self.min_pattern_len - 1

        self._bit_writer = BitWriter(f)

        self.buffer = bytearray(2**self.window_bits)
        self.buffer_pos = 0

        # Write header
        self._bit_writer.write(window - 8, 3)
        self._bit_writer.write(size - 4, 2)
        self._bit_writer.write(literal - 5, 2)
        self._bit_writer.write(0, 1)  # No other header bytes

    @micropython.viper
    def compress(self, data_bytes):
        self.buffer_pos = self._compress(data_bytes)

    @micropython.viper
    def _compress(self, data_bytes) -> int:
        data_len = int(len(data_bytes))
        data_len_minus_1 = data_len - 1
        data = ptr8(data_bytes)

        buffer = ptr8(self.buffer)
        buffer_len = int(len(self.buffer))
        buffer_pos = int(self.buffer_pos)

        min_pattern_len = int(self.min_pattern_len)
        max_pattern_len = int(self.max_pattern_len)
        size_bits = int(self.size_bits)
        literal_bits = int(self.literal_bits)
        literal_flag = 1 << literal_bits
        literal_mask_check = int(0xFFFFFFFF) - literal_flag + 1

        data_pos = int(0)
        # We perform 2 execution shortcuts (manually checking first 2 bytes for match).
        # This could result in an out-of-bounds pattern match.
        # We compensate here with ``data_len_minus_1`` so we don't need to perform
        # additional (rare) boundary checks inside a super tight loop.
        while data_pos < data_len_minus_1:
            # Find longest pattern match
            best_buffer_pos = int(0)
            best_pattern_len = int(0)
            for buffer_search_start in range(buffer_len - min_pattern_len + 1):
                if buffer[buffer_search_start] != data[data_pos]:
                    # Execution shortcut; first symbol usually doesn't match.
                    continue

                if buffer[buffer_search_start + 1] != data[data_pos + 1]:
                    # Execution shortcut; a pattern doesn't exist.
                    continue

                for pattern_len in range(2, max_pattern_len + 1):
                    buffer_search_pos = buffer_search_start + pattern_len
                    data_search_pos = data_pos + pattern_len

                    if buffer[buffer_search_pos] != data[data_search_pos]:
                        break
                    # Bounds check after; less likely to perform check.
                    if buffer_search_pos >= buffer_len:
                        break
                    if data_search_pos >= data_len:
                        break

                if pattern_len > best_pattern_len:
                    best_buffer_pos = buffer_search_start
                    best_pattern_len = pattern_len
                    if pattern_len == max_pattern_len:
                        break

            # Write out a literal or a token
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
                if data[data_pos] & literal_mask_check:
                    raise ExcessBitsError
                self._bit_writer.write(data[data_pos] | literal_flag, literal_bits + 1)
                buffer[buffer_pos] = data[data_pos]
                buffer_pos = (buffer_pos + 1) % buffer_len
                data_pos += 1

        if data_pos == data_len_minus_1:
            if data[data_pos] & literal_mask_check:
                raise ExcessBitsError
            self._bit_writer.write(data[data_pos] | literal_flag, literal_bits + 1)
            buffer[buffer_pos] = data[data_pos]
            buffer_pos = (buffer_pos + 1) % buffer_len
            data_pos += 1

        return buffer_pos

    def flush(self):
        self._bit_writer.flush()
