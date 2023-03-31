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


class _BufferedWriter:
    """Buffers up to 8 tokens/literals and writes it with grouped flags to disk."""

    def __init__(self, f):
        self.f = f
        self.buf = memoryview(bytearray(17))  # 8 tokens plus 1 flag byte
        self.buf_i = 1
        self.flags = self.buf[:1]
        self.n_tokens = 0

    def write_literal(self, c):
        self.buf[self.buf_i] = c
        self.buf_i += 1
        self.n_tokens += 1
        if self.n_tokens == 8:
            self.flush()

    def write_reference(self, pos, size):
        size = size - 3  # Minimum stored size is 3
        self.flags[0] |= 1 << self.n_tokens
        self.buf[self.buf_i : self.buf_i + 2] = (pos << 4 | size).to_bytes(2, "little")
        self.buf_i += 2
        self.n_tokens += 1

        if self.n_tokens == 8:
            self.flush()

    def flush(self):
        self.f.write(self.buf[: self.buf_i])
        self.buf_i = 1
        self.n_tokens = 0
        self.flags[0] = 0


class _BufferedReader:
    """Decodes if read value is a token or literal."""

    def __init__(self, f):
        self.f = f

    def read(self, size):
        raise NotImplementedError


class Compressor:
    def __init__(self, f):
        self._writer = _BufferedWriter(f)
        self.buf = bytearray(4096)
        self.buf_start = 0

    def compress(self, data):
        data_start = 0
        while data_start < len(data):
            search_i = 0
            match_size = 1
            for size in range(3, 19):  # start search at length(3) token
                data_end = data_start + size
                if data_end > len(data):
                    break
                next_string = data[data_start:data_end]
                try:
                    search_i = self.buf.index(next_string, search_i)  # ~28% of time
                except ValueError:
                    break  # Not Found
                string = next_string
                match_size = size

            # print(f"{match_size=} {search_i=} {self.buf_start=} {len(self.buf)=}")
            if match_size > 1:
                self._writer.write_reference(search_i, match_size)

                # need to add to buffer
                buf_end = self.buf_start + match_size
                start_length = buf_end - len(self.buf)
                if start_length > 0:
                    # At buffer wraparound point; Need to do 2 writes
                    self.buf[self.buf_start : len(self.buf)] = string[:-start_length]
                    self.buf[:start_length] = string[-start_length:]
                else:
                    self.buf[self.buf_start : buf_end] = string
            else:
                self.buf[self.buf_start] = data[data_start]
                self._writer.write_literal(data[data_start])

            self.buf_start += match_size
            if self.buf_start >= 4096:
                self.buf_start -= 4096

            data_start += match_size

    def flush(self):
        self._writer.flush()


class Decompressor:
    def __init__(self, f):
        self._reader = _BufferedReader(f)
        raise NotImplementedError

    def decompress(self):
        raise NotImplementedError


def main():
    import time
    from io import BytesIO

    # test_string = b"the quick brown fox jumped over the lazy dog." * 100
    block_size = 1024 * 1024
    uncompressed_len = 0
    expected_uncompressed_len = 100000000
    t_start = time.time()
    with open("compressed.lzss", "wb") as compressed_f:
        compressor = Compressor(compressed_f)
        with open("enwik8", "rb") as f:
            while True:
                print(f"{100 * uncompressed_len / expected_uncompressed_len:.1f}%")
                data = f.read(block_size)
                if not data:
                    break
                uncompressed_len += len(data)
                compressor.compress(data)
        compressor.flush()
        compressed_len = compressed_f.tell()
        print(f"compressed={compressed_len}")
        print(f"ratio: {uncompressed_len / compressed_len:.3f}")

        """
        f.seek(0)
        decompressor = Decompressor(f)
        result = decompressor.decompress()
        assert result == test_string
        print(f"{len(test_string)=}")
        """

    t_end = time.time()
    t_duration = t_end - t_start
    print(f"{t_duration=}")


if __name__ == "__main__":
    main()
