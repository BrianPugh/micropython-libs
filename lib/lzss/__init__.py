class ExcessBitsError(Exception):
    """Provided data has more bits than expected."""


def compute_min_pattern_bytes(window_bits, size_bits, literal_bits):
    return int((window_bits + size_bits) / (literal_bits + 1) + 1.001)


try:
    from .compressor_viper import Compressor
except ImportError:
    try:
        from .compressor import Compressor
    except ImportError:
        pass

try:
    from .decompressor_viper import Decompressor
except ImportError:
    try:
        from .decompressor import Decompressor
    except ImportError:
        pass
