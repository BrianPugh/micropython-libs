"""
"""
import io
import random
import unittest

from lzss import Compressor, Decompressor
from lzss.compressor import BitWriter
from lzss.decompressor import BitReader


class TestBitWriterAndReader(unittest.TestCase):
    def test_auto_bit_writer_and_reader(self):
        # Generate a list of random chunks of bits (1~16 bits)
        num_chunks = 1000
        n_bits = [random.randint(1, 16) for _ in range(num_chunks)]
        data = []
        for n_bit in n_bits:
            mask = (1 << n_bit) - 1
            data.append(random.randint(0, 1 << 32) & mask)
        chunks = list(zip(data, n_bits))

        # Write the chunks of bits using BitWriter
        with io.BytesIO() as f:
            writer = BitWriter(f)
            for bits, num_bits in chunks:
                writer.write(bits, num_bits)
            writer.flush()

            # Read the chunks of bits back using BitReader and compare with original data
            f.seek(0)
            reader = BitReader(f)
            for original_bits, num_bits in chunks:
                read_bits = reader.read(num_bits)
                self.assertEqual(read_bits, original_bits)

    def test_compressor(self):
        test_string = b"foo foo foo"

        expected = bytes(
            [
                0b010_00_110,  # , header (window_bits=10, size_bits=4, literal_bits=8)
                0b1_0110_011,  # f; 1 flag; carry 0
                0b0_1_0110_11,  # o; 1 flag; carry 11
                0b11_1_0110_1,  # o; 1 flag, carry 111
                0b111_1_0010,  # space; 1 flag, carry 0000
                # FIRST TOKEN, should be a repeat of "foo " at index 0
                0b0000_0_000,
                0b0000000_0,  # "foo " token <0, 4> -> <0, 2>; 0 flag, carry 010
                # SECOND TOKEN, should be a repeat of "foo" at index 0
                0b010_0_0000,
                0b000000_00,  # "foo" token <0, 3> -> <0, 1>; carry 01
                0b0100_0000,
            ]
        )
        with io.BytesIO() as f:
            compressor = Compressor(f)
            compressor.compress(test_string)
            compressor.flush()

            f.seek(0)
            actual = f.read()
        self.assertEqual(actual, expected)

    def test_decompressor(self):
        expected = b"foo foo foo"
        # WINDOW_BITS = 10
        # SIZE_BITS = 4
        # MIN_PATTERN_BYTES = 2

        compressed = bytes(
            [
                0b010_00_110,  # , header (window_bits=10, size_bits=4, literal_bits=8)
                0b1_0110_011,  # f; 1 flag; carry 0
                0b0_1_0110_11,  # o; 1 flag; carry 11
                0b11_1_0110_1,  # o; 1 flag, carry 111
                0b111_1_0010,  # space; 1 flag, carry 0000
                # FIRST TOKEN, should be a repeat of "foo " at index 0
                0b0000_0_000,
                0b0000000_0,  # "foo " token <0, 4> -> <0, 2>; 0 flag, carry 010
                # SECOND TOKEN, should be a repeat of "foo" at index 0
                0b010_0_0000,
                0b000000_00,  # "foo" token <0, 3> -> <0, 1>; carry 01
                0b0100_0000,
            ]
        )

        with io.BytesIO(compressed) as f:
            decompressor = Decompressor(f)
            actual = decompressor.decompress()

        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
