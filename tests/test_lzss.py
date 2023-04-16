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

    def test_writer_correct_length(self):
        for i in range(1, 8 + 1):
            with io.BytesIO() as f:
                writer = BitWriter(f)
                writer.write(0xFFFF, i)
                writer.flush()

                self.assertEqual(f.tell(), 1)
        for i in range(9, 16 + 1):
            with io.BytesIO() as f:
                writer = BitWriter(f)
                writer.write(0xFFFF, i)
                writer.flush()

                self.assertEqual(f.tell(), 2)


class TestCompressor(unittest.TestCase):
    def test_compressor_default(self):
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

    def test_compressor_7bit(self):
        test_string = b"foo foo foo"

        expected = bytes(
            [
                0b010_00_100,  # , header (window_bits=10, size_bits=4, literal_bits=7)
                0b1_110_0110,  # f; 1 flag
                0b1_110_1111,  # o; 1 flag
                0b1_110_1111,  # o; 1 flag
                0b1_010_0000,  # space; 1 flag
                # FIRST TOKEN, should be a repeat of "foo " at index 0
                0b0_0000000,  # "foo " token <0, 4> -> <0, 2>; 0 flag
                0b000_0010_0,  # reverse-carry flag from next token
                # SECOND TOKEN, should be a repeat of "foo" at index 0
                0b00000000,  # "foo" token <0, 3> -> <0, 1>
                0b00_0001_00,  # 2bit padding.
            ]
        )
        with io.BytesIO() as f:
            compressor = Compressor(f, literal=7)
            compressor.compress(test_string)
            compressor.flush()

            f.seek(0)
            actual = f.read()
        self.assertEqual(actual, expected)

    def test_oob_2_byte_pattern(self):
        """Viper implementation had a bug where a pattern of length 2
        could be detected at the end of a string (going out of bounds
        by 1 byte).
        """
        test_string_extended = bytearray(b"Q\x00Q\x00")
        test_string = memoryview(test_string_extended)[:3]

        with io.BytesIO() as f:
            compressor = Compressor(f)
            compressor.compress(test_string)
            compressor.flush()

            f.seek(0)
            actual = f.read()
        assert actual == b"F\xa8\xc0* "


class TestDecompressor(unittest.TestCase):
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

    def test_decompressor_restricted_size(self):
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
            self.assertEqual(decompressor.decompress(4), b"foo ")
            self.assertEqual(decompressor.decompress(2), b"fo")
            self.assertEqual(decompressor.decompress(-1), b"o foo")


class TestCompressorAndDecompressor(unittest.TestCase):
    def _autotest(self, num_bytes, n_bits, compressor_kwargs=None):
        if compressor_kwargs is None:
            compressor_kwargs = {}

        data = bytearray(random.randint(0, (1 << n_bits) - 1) for x in range(num_bytes))

        with io.BytesIO() as f:
            c = Compressor(f, **compressor_kwargs)
            c.compress(data)
            c.flush()

            f.seek(0)
            d = Decompressor(f)
            actual = d.decompress()

        self.assertEqual(actual, data)

        data = bytearray(1 for _ in range(num_bytes))
        with io.BytesIO() as f:
            c = Compressor(f, **compressor_kwargs)
            c.compress(data)
            c.flush()

            f.seek(0)
            d = Decompressor(f)
            actual = d.decompress()

        self.assertEqual(len(actual), len(data))
        self.assertEqual(actual, data)

    def test_default(self):
        self._autotest(10_000, 8)

    def test_7bit(self):
        self._autotest(10_000, 7, compressor_kwargs={"literal": 7})

    def test_6bit(self):
        self._autotest(10_000, 6, compressor_kwargs={"literal": 6})

    def test_5bit(self):
        self._autotest(10_000, 5, compressor_kwargs={"literal": 5})


if __name__ == "__main__":
    unittest.main()
