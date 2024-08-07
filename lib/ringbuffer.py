from array import array


class RingBuffer:
    """Simple RingBuffer/CircularBuffer.

    Commonly used for moving-window-averages and the like.
    """

    def __init__(self, size, dtype="f"):
        """Create a RingBuffer.

        Parameters
        ----------
        size: int
            Size of RingBuffer.
        dtype: str
            Type code for what each element represents.
            Defaults to ``"f"`` for float.
            +--------+--------------------+------+
            | dtype  | C Type             | Size |
            +========+====================+======+
            | 'b'    | signed char        | 1    |
            | 'B'    | unsigned char      | 1    |
            | 'h'    | signed short       | 2    |
            | 'H'    | unsigned short     | 2    |
            | 'i'    | signed int         | 2    |
            | 'I'    | unsigned int       | 2    |
            | 'l'    | signed long        | 4    |
            | 'L'    | unsigned long      | 4    |
            | 'q'    | signed long long   | 8    |
            | 'Q'    | unsigned long long | 8    |
            | 'f'    | float (DEFAULT)    | 4    |
            | 'd'    | double             | 8    |
            +--------+--------------------+------+
        """
        if size <= 0:
            raise ValueError

        self.buffer = array(dtype, (0 for _ in range(size)))
        self._max_size = size
        self._index = 0
        self._size = 0

    def __len__(self):
        """Amount ring buffer has been filled."""
        return self._size

    def __getitem__(self, index):
        """Get value from ring buffer where ``0`` is oldest, and ``-1`` or is newest."""
        index = (index + self._index) % self._size
        return self.buffer[index]

    def __repr__(self):
        return f"RingBuffer(size={self._max_size}, buffer={repr(self.buffer)})"

    def __iter__(self):
        """Iterate oldest to newest values."""
        for i in range(len(self)):
            yield self[i]

    def __eq__(self, other):
        try:
            iter(other)
        except TypeError:
            # Not Iterable
            return False

        if len(self) != len(other):
            return False

        return all(x == y for x, y in zip(self, other))

    @property
    def max_size(self):
        """Maximum number of elements in RingBuffer."""
        return self._max_size

    @property
    def full(self):
        """RingBuffer is fully populated."""
        return self._size == self.max_size

    def append(self, val):
        self.buffer[self._index] = val
        self._index = (self._index + 1) % self.max_size
        if not self.full:
            self._size += 1

    def mean(self):
        """Average of populated RingBuffer elements.

        Raises
        ------
        ZeroDivisionError
            If the RingBuffer is empty.
        """
        return sum(self.buffer[: self._size]) / self._size

    def median(self):
        """Median of populated RingBuffer elements.

        Raises
        ------
        ZeroDivisionError
            If the RingBuffer is empty.
        """
        vals = sorted(self)
        index, is_odd = len(vals) // 2, len(vals) % 2
        return vals[index] if is_odd else (self[index] + self[index - 1]) / 2

    def diff(self):
        """Finite difference."""
        for i in range(len(self) - 1):
            yield self[i + 1] - self[i]

    def max(self):
        """Maximum of populated RingBuffer elements."""
        return max(self.buffer[: self._size])

    def min(self):
        """Minimum of populated RingBuffer elements."""
        return min(self.buffer[: self._size])

    def clear(self):
        """Reset the RingBuffer."""
        self._index = 0
        self._size = 0
