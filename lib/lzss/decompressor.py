from . import compute_min_pattern_bytes


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


class Decompressor:
    def __init__(self, f):
        self._bit_reader = BitReader(f)

        # Read Header
        self.window_bits = self._bit_reader.read(3) + 8
        self.size_bits = self._bit_reader.read(2) + 4
        self.literal_bits = self._bit_reader.read(2) + 5

        if self._bit_reader.read(1):
            raise NotImplementedError

        # Setup buffers
        self.min_pattern_bytes = compute_min_pattern_bytes(
            self.window_bits, self.size_bits, self.literal_bits
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
                    c = self._bit_reader.read(self.literal_bits)
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
