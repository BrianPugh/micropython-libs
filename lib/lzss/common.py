class RingBuffer:
    """Simple write-only ring buffer for storing window."""

    def __init__(self, size):
        self.buffer = bytearray(size)
        self.size = size
        self.pos = 0

        if not hasattr(self, "index"):
            self.index = self.buffer.index

    if not hasattr(bytearray, "index"):
        import micropython

        @micropython.viper
        def index(self, sub, start: int) -> int:
            buf_ptr = ptr8(self.buffer)
            sub_ptr = ptr8(sub)

            start = int(start)
            buf_len = int(len(self.buffer))
            sub_len = int(len(sub))

            for i in range(start, buf_len - sub_len + 1):
                for j in range(sub_len):
                    if buf_ptr[i + j] != sub_ptr[j]:
                        break
                else:
                    return i
            raise ValueError

    def write_byte(self, byte):  # ~10% of time
        self.buffer[self.pos] = byte
        self.pos = (self.pos + 1) % self.size

    def write_bytes(self, data):
        buffer = self.buffer
        pos = self.pos
        size = self.size
        for byte in data:
            buffer[pos] = byte
            pos = (pos + 1) % size
        self.pos = pos


t = 0


def timed_function(f, *args, **kwargs):
    import time

    def new_func(*args, **kwargs):
        global t
        t_start = time.ticks_us()
        result = f(*args, **kwargs)
        t += time.ticks_diff(time.ticks_us(), t_start)
        return result

    return new_func
