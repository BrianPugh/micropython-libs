import pytest
from ringbuffer import RingBuffer


def test_ring_buffer_various():
    ring_buffer = RingBuffer(3)
    assert len(ring_buffer) == 0
    assert ring_buffer.max_size == 3
    assert not ring_buffer.full
    with pytest.raises(ZeroDivisionError):
        ring_buffer.mean()
    with pytest.raises(ZeroDivisionError):
        ring_buffer.median()

    # [2,]
    ring_buffer.append(2)
    assert len(ring_buffer) == 1
    assert ring_buffer.mean() == 2
    assert ring_buffer.median() == 2
    assert ring_buffer.max() == 2
    assert ring_buffer.min() == 2
    assert not ring_buffer.full
    assert ring_buffer[0] == 2

    # [2, 4,]
    ring_buffer.append(4)
    assert len(ring_buffer) == 2
    assert ring_buffer.mean() == 3
    assert ring_buffer.median() == 3
    assert ring_buffer.max() == 4
    assert ring_buffer.min() == 2
    assert not ring_buffer.full
    assert ring_buffer[0] == 2
    assert ring_buffer[1] == 4

    # [2, 4, 6,]
    ring_buffer.append(6)
    assert len(ring_buffer) == 3
    assert ring_buffer.mean() == 4
    assert ring_buffer.median() == 4
    assert ring_buffer.max() == 6
    assert ring_buffer.min() == 2
    assert ring_buffer.full
    assert ring_buffer[0] == 2
    assert ring_buffer[1] == 4
    assert ring_buffer[2] == 6

    # [4, 6, 8,]
    ring_buffer.append(8)
    assert len(ring_buffer) == 3
    assert ring_buffer.mean() == 6
    assert ring_buffer.median() == 6
    assert ring_buffer.max() == 8
    assert ring_buffer.min() == 4
    assert ring_buffer.full
    assert ring_buffer[0] == 4
    assert ring_buffer[1] == 6
    assert ring_buffer[2] == 8

    ring_buffer.clear()

    assert len(ring_buffer) == 0
    assert ring_buffer.max_size == 3
    assert not ring_buffer.full


def test_ring_buffer_invalid_size():
    with pytest.raises(ValueError):
        RingBuffer(0)

    with pytest.raises(ValueError):
        RingBuffer(-1)


@pytest.fixture
def fib_rb():
    ring_buffer = RingBuffer(5)
    ring_buffer.append(1)
    ring_buffer.append(1)
    ring_buffer.append(2)
    ring_buffer.append(3)
    ring_buffer.append(5)
    return ring_buffer


def test_ring_buffer_iter(fib_rb):
    assert list(fib_rb) == [1, 1, 2, 3, 5]


def test_ring_buffer_eq(fib_rb):
    assert fib_rb == [1, 1, 2, 3, 5]

    assert fib_rb != [1, 1, 2, 3, 6]
    assert fib_rb != [1, 1, 2, 3]
    assert fib_rb != 0


def test_ring_buffer_diff(fib_rb):
    assert list(fib_rb.diff()) == [0, 1, 1, 2]
