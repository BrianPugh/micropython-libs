class Oversample:
    def __init__(self, f, n):
        """Oversample a sensor.

        Oversampling will improve the SNR and measurement resolution at the cost
        of increased CPU utilization and reduced throughput.

        +--------------+------------------+
        | N Samples    | Additional Bits  |
        +==============+==================+
        |            1 |                0 |
        +--------------+------------------+
        |            4 |                1 |
        +--------------+------------------+
        |           16 |                2 |
        +--------------+------------------+
        |           64 |                3 |
        +--------------+------------------+
        |          256 |                4 |
        +--------------+------------------+
        |         1024 |                5 |
        +--------------+------------------+
        |         4096 |                6 |
        +--------------+------------------+
        |        16384 |                7 |
        +--------------+------------------+
        |        65536 |                8 |
        +--------------+------------------+

        Further Reading:
            https://www.silabs.com/documents/public/application-notes/an118.pdf

        Parameters
        ----------
        f: callable
            Some callable function that takes no argumments and returns a number.
        n: int
            Number of timmes to sample ``f``.
        """
        self.f = f
        self.n = n

    def __call__(self):
        return oversample(self.f, self.n)


def oversample(f, n):
    """Oversample a sensor.

    Oversampling will improve the SNR and measurement resolution at the cost
    of increased CPU utilization and reduced throughput.

    Further Reading:
        https://www.silabs.com/documents/public/application-notes/an118.pdf

    Parameters
    ----------
    f: callable
        Some callable function that takes no argumments and returns a number.
    n: int
        Number of timmes to sample ``f``.
    """
    sigma = 0
    for _ in range(n):
        sigma += f()
    return sigma / n
