import pytest
from ringbuffer import RingBuffer


def test_ring_buffer_various():
    ring_buffer = RingBuffer(3)
    assert len(ring_buffer) == 0
    assert ring_buffer.max_size == 3
    assert not ring_buffer.full

    ring_buffer.append(2)
    assert len(ring_buffer) == 1
    assert ring_buffer.mean() == 2
    assert ring_buffer.max() == 2
    assert ring_buffer.min() == 2
    assert not ring_buffer.full
    assert ring_buffer[0] == 2

    ring_buffer.append(4)
    assert len(ring_buffer) == 2
    assert ring_buffer.mean() == 3
    assert ring_buffer.max() == 4
    assert ring_buffer.min() == 2
    assert not ring_buffer.full
    assert ring_buffer[0] == 2
    assert ring_buffer[1] == 4

    ring_buffer.append(6)
    assert len(ring_buffer) == 3
    assert ring_buffer.mean() == 4
    assert ring_buffer.max() == 6
    assert ring_buffer.min() == 2
    assert ring_buffer.full
    assert ring_buffer[0] == 2
    assert ring_buffer[1] == 4
    assert ring_buffer[2] == 6

    ring_buffer.append(8)
    assert len(ring_buffer) == 3
    assert ring_buffer.mean() == 6
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
