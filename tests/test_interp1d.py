import interp1d
import pytest


def test_searchsorted_odd():
    a = [2, 10, 12]

    assert interp1d.searchsorted(a, -1) == 0
    assert interp1d.searchsorted(a, 0) == 0
    assert interp1d.searchsorted(a, 2) == 0
    assert interp1d.searchsorted(a, 5) == 1
    assert interp1d.searchsorted(a, 10) == 1
    assert interp1d.searchsorted(a, 11) == 2
    assert interp1d.searchsorted(a, 12) == 2
    assert interp1d.searchsorted(a, 13) == 3
    assert interp1d.searchsorted(a, 14) == 3


def test_searchsorted_even():
    a = [0, 2, 10, 12]

    assert interp1d.searchsorted(a, -1) == 0
    assert interp1d.searchsorted(a, 0) == 0
    assert interp1d.searchsorted(a, 1) == 1
    assert interp1d.searchsorted(a, 2) == 1
    assert interp1d.searchsorted(a, 5) == 2
    assert interp1d.searchsorted(a, 10) == 2
    assert interp1d.searchsorted(a, 11) == 3
    assert interp1d.searchsorted(a, 12) == 3
    assert interp1d.searchsorted(a, 13) == 4
    assert interp1d.searchsorted(a, 14) == 4


@pytest.mark.parametrize(
    "v, expected", [(0, 0), (0.3, 12), (1.7, 33), (2.7, 44), (7, 33.3333), (13.0, 1)]
)
def test_linear_interpolate(v, expected):
    x = [0, 1, 2, 3, 5, 8, 13]
    y = [0, 40, 30, 50, 20, 40, 1]

    interpolater = interp1d.Linear(x, y)
    assert pytest.approx(expected, 0.01) == interpolater(v)


@pytest.mark.parametrize("v", [-1, 13.2])
def test_linear_out_of_range(v):
    x = [0, 1, 2, 3, 5, 8, 13]
    y = [0, 40, 30, 50, 20, 40, 1]

    interpolater = interp1d.Linear(x, y)
    with pytest.raises(IndexError):
        interpolater(v)


def test_interpolater_mismatch_lens():
    with pytest.raises(ValueError):
        interp1d.Interpolater([1, 2, 3], [4, 5])


def test_interpolater_len():
    interpolater = interp1d.Interpolater([1, 2, 3], [4, 5, 6])
    assert len(interpolater) == 3


@pytest.mark.parametrize(
    "v, expected",
    [(0, 0), (0.3, 11.38), (1.7, 30.33), (2.7, 42.58), (7, 29.36), (13.0, 1)],
)
def test_cubic_interpolate(v, expected):
    x = [0, 1, 2, 3, 5, 8, 13]
    y = [0, 40, 30, 50, 20, 40, 1]

    interpolater = interp1d.Cubic(x, y)
    assert pytest.approx(expected, 0.01) == interpolater(v)


@pytest.mark.skip(reason="visualization")
def test_cubic_interpolate_visual():
    x = [0, 1, 2, 3, 5, 8, 13]
    y = [0, 40, 30, 50, 20, 40, 1]

    interpolater = interp1d.Cubic(x, y)

    interp_x = [z / 100 for z in range(1300)]
    interp_y = [interpolater(z) for z in interp_x]
    import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]

    plt.plot(interp_x, interp_y)
    plt.plot(x, y)
    plt.show()


@pytest.mark.parametrize(
    "v, expected",
    [(0, 0), (0.3, 18.20), (1.7, 32.16), (2.7, 45.68), (7, 34.81), (13.0, 1)],
)
def test_monospline_interpolate(v, expected):
    x = [0, 1, 2, 3, 5, 8, 13]
    y = [0, 40, 30, 50, 20, 40, 1]

    interpolater = interp1d.MonoSpline(x, y)
    assert pytest.approx(expected, 0.01) == interpolater(v)


@pytest.mark.skip(reason="visualization")
def test_monospline_interpolate_visual():
    x = [0, 1, 2, 3, 5, 8, 13]
    y = [0, 40, 30, 50, 20, 40, 1]

    interpolater = interp1d.MonoSpline(x, y)

    interp_x = [z / 100 for z in range(1300)]
    interp_y = [interpolater(z) for z in interp_x]
    import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]

    plt.plot(interp_x, interp_y)
    plt.plot(x, y)
    plt.show()
