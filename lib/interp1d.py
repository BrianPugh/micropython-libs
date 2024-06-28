"""Data interpolation with no dependencies."""

from array import array
from math import pow, sqrt


def _diff(x):
    """Compute the finite difference of iterable ``x``."""
    return array("f", (b - a for a, b in zip(x[:-1], x[1:])))


def _div(a, b):
    return array("f", (a_i / b_i for a_i, b_i in zip(a, b)))


def searchsorted(a, v):
    """Find indices where elements should be inserted to maintain order.

    Parameters
    ----------
    a: Union[list, array]
        Sorted values.
    v: float
        Value to be inserted

    Returns
    -------
    int
        Index into ``a`` that ``v`` can be inserted and maintain order.
    """
    low_index = 0
    mid_index = -1
    high_index = len(a) - 1

    while low_index <= high_index:
        mid_index = (low_index + high_index) // 2

        if a[mid_index] > v:
            high_index = mid_index - 1
        elif a[mid_index] < v:
            low_index = mid_index + 1
        else:
            return mid_index

    return low_index


class Interpolater:
    def __init__(self, x, y, fill_value=None):
        """Abstract interpolater base class.

        Parameters
        ----------
        x : Union[list, array]
            Sorted input values.
        y : Union[list, array]
            Corresponding output values.
        fill_value: Optional[tuple[float, float]]
            If ``None``, input values outside the range of ``x`` will raise a ``ValueError``.
            If a two-element ``tuple``, values below ``x[0]`` will return ``fill_value[0]``,
            and values above ``x[-1]`` will return ``fill_value[1]``.
            If the string ``"clip"``, will clip inputs to range of ``x``.
        """
        if len(x) != len(y) or len(x) <= 1:
            raise ValueError

        self.x = [float(v) for v in x]
        self.y = [float(v) for v in y]
        self.size = len(x)
        if fill_value == "clip":
            self.fill_value = (self.y[0], self.y[-1])
        elif fill_value is None or (isinstance(fill_value, tuple) and len(fill_value) == 2):
            self.fill_value = fill_value
        else:
            raise ValueError

    def __len__(self):
        """Return the number of datapoints."""
        return self.size

    def __call__(self, v):
        """Calculate interpolated output value for input ``v``."""
        if v < self.x[0]:
            if self.fill_value:
                return self.fill_value[0]
            else:
                raise ValueError
        if v > self.x[-1]:
            if self.fill_value:
                return self.fill_value[1]
            else:
                raise ValueError
        return self._compute(v)

    def _compute(self, v):
        """Subclass computes output value for input ``v``."""
        raise NotImplementedError

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    @classmethod
    def from_dict(cls, d, *args, **kwargs):
        """Create Interpolater from dictionary mapping ``x`` to ``y``."""
        return cls(*zip(*sorted(d.items())), *args, **kwargs)


def _linear_interpolation(x, y, v):
    high_i = searchsorted(x, v)

    high_x = x[high_i]
    if high_x == v:
        return y[high_i]

    low_x = x[high_i - 1]
    low_y = y[high_i - 1]
    high_y = y[high_i]

    p = (v - low_x) / (high_x - low_x)

    return p * high_y + (1 - p) * low_y


class Linear(Interpolater):
    """Simple linear interpolation."""

    def _compute(self, v):
        return _linear_interpolation(self.x, self.y, v)


class Cubic(Interpolater):
    """Interpolate using cubic splines.

    Based on:
        https://stackoverflow.com/a/48085583
    """

    def __init__(self, x, y, *args, **kwargs):
        super().__init__(x, y, *args, **kwargs)

        size = self.size

        if size == 2:
            return  # Will perform linear interpolation.

        xdiff, ydiff = _diff(x), _diff(y)

        # allocate buffer matrices
        li = array("f", (0 for _ in range(size)))
        li_1 = array("f", (0 for _ in range(size - 1)))
        z = array("f", (0 for _ in range(size)))

        # fill diagonals Li and Li-1 and solve [L][y] = [B]
        li[0] = sqrt(2 * xdiff[0])
        li_1[0] = 0.0
        b0 = 0.0  # natural boundary
        z[0] = b0 / li[0]

        for i in range(1, size - 1, 1):
            li_1[i] = xdiff[i - 1] / li[i - 1]
            li[i] = sqrt(2 * (xdiff[i - 1] + xdiff[i]) - li_1[i - 1] * li_1[i - 1])
            bi = 6 * (ydiff[i] / xdiff[i] - ydiff[i - 1] / xdiff[i - 1])
            z[i] = (bi - li_1[i - 1] * z[i - 1]) / li[i]

        i = size - 1
        li_1[i - 1] = xdiff[-1] / li[i - 1]
        li[i] = sqrt(2 * xdiff[-1] - li_1[i - 1] * li_1[i - 1])
        bi = 0.0  # natural boundary
        z[i] = (bi - li_1[i - 1] * z[i - 1]) / li[i]

        # solve [L.T][x] = [y]
        i = size - 1
        z[i] = z[i] / li[i]
        for i in range(size - 2, -1, -1):
            z[i] = (z[i] - li_1[i - 1] * z[i + 1]) / li[i]

        self.z = z

    def _compute(self, v):
        if self.size == 2:
            return _linear_interpolation(self.x, self.y, v)

        x, y, z = self.x, self.y, self.z

        # find index
        index = searchsorted(x, v)
        index = min(self.size - 1, max(1, index))

        xi1, xi0 = x[index], x[index - 1]
        yi1, yi0 = y[index], y[index - 1]
        zi1, zi0 = z[index], z[index - 1]
        hi1 = xi1 - xi0

        # calculate cubic
        f0 = (
            zi0 / (6 * hi1) * (xi1 - v) ** 3
            + zi1 / (6 * hi1) * (v - xi0) ** 3
            + (yi1 / hi1 - zi1 * hi1 / 6) * (v - xi0)
            + (yi0 / hi1 - zi0 * hi1 / 6) * (xi1 - v)
        )
        return f0


class MonoSpline(Interpolater):
    """Interpolate using monotone cubic splines.

    Based on:
        https://github.com/antdvid/MonotonicCubicInterpolation
    """

    def __init__(self, x, y, *args, **kwargs):
        super().__init__(x, y, *args, **kwargs)

        if self.size == 2:
            return  # Will perform linear interpolation.

        self.h = _diff(x)
        self.m = _div(_diff(y), self.h)
        self.b = self._compute_b()

        # fmt: off
        self.c = array("f", (
            (3 * m_i - b1_i - 2 * b2_i) / h_i
            for    m_i,       b1_i,        b2_i,    h_i in  # noqa: E271
            zip(self.m, self.b[1:], self.b[:-1], self.h)
        ))
        self.d = array("f", (
            (b1_i + b2_i - 2 * m_i) / (h_i * h_i)
            for    m_i,       b1_i,   b2_i, h_i in  # noqa: E271
            zip(self.m, self.b[1:], self.b[:-1], self.h)
        ))
        # fmt: on

    def _compute_b(self):
        b = array("f", (0 for _ in range(self.size)))
        for i in range(1, self.size - 1):
            is_mono = self.m[i - 1] * self.m[i] > 0
            if is_mono:
                # fmt: off
                b[i] = (
                    3 * self.m[i - 1] * self.m[i] / (
                        max(self.m[i - 1], self.m[i])
                        + 2 * min(self.m[i - 1], self.m[i])
                    )
                )
                # fmt: on
            else:
                b[i] = 0
            if is_mono and self.m[i] > 0:
                b[i] = min(max(0, b[i]), 3 * min(self.m[i - 1], self.m[i]))
            elif is_mono and self.m[i] < 0:
                b[i] = max(min(0, b[i]), 3 * max(self.m[i - 1], self.m[i]))

        b[0] = ((2 * self.h[0] + self.h[1]) * self.m[0] - self.h[0] * self.m[1]) / (self.h[0] + self.h[1])
        b[-1] = ((2 * self.h[-1] + self.h[-2]) * self.m[-1] - self.h[-1] * self.m[-2]) / (self.h[-1] + self.h[-2])
        return b

    def _compute(self, v):
        if self.size == 2:
            return _linear_interpolation(self.x, self.y, v)

        x = self.x
        i = max(0, searchsorted(x, v) - 1)
        i = min(i, self.size - 2)
        return self.y[i] + self.b[i] * (v - x[i]) + self.c[i] * pow(v - x[i], 2.0) + self.d[i] * pow(v - x[i], 3.0)
