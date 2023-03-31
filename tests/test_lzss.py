import io
import random
import unittest

from lzss import BitReader, BitWriter


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


if __name__ == "__main__":
    unittest.main()
