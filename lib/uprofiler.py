from time import ticks_diff, ticks_us  # type: ignore[reportGeneralTypeIssues]

_t_import = ticks_us()

_BOLD = "\033[1m"
_RESET = "\033[0m"

# Default print period
print_period = 1


def _ticks_delta(t_start):
    return ticks_diff(ticks_us(), t_start)


class _Counter:
    registry = {}

    def __init__(self, name, print_period):
        self.name = name
        self.print_period = print_period
        self.n = 0
        self.t_time_us = 0

        self.registry[name] = self

    def record(self, delta):
        self.n += 1
        self.t_time_us += delta

    @property
    def average(self):
        return self.t_time_us / self.n

    def __str__(self):
        t_time_ms = self.t_time_us / 1000
        return f"{self.name: 24.24} {self.n : >8} calls {t_time_ms:>12.3f}ms total {t_time_ms/self.n:>12.3f}ms average"

    def print(self):
        pp = self.print_period
        if pp is None:
            pp = print_period

        if pp > 0 and self.n % pp == 0:
            print(self)


class profile:
    """Function decorator and context manager profile."""

    def __init__(self, f=None, *, name=None, print_period=None):
        self.name = name
        self.print_period = print_period
        self._f_init(f)

    def _f_init(self, f):
        self.f = f
        if f is not None:
            self.__name__ = f.__name__
            if self.name is None:
                self.name = f.__name__
            self.counter = _Counter(self.name, self.print_period)

    def __call__(self, *args, **kwargs):
        if self.f is None:  # was originally called with decorator args
            self._f_init(args[0])
            return self

        t_start = ticks_us()
        result = self.f(*args, **kwargs)
        delta = _ticks_delta(t_start)
        self.counter.record(delta)
        self.counter.print()

        return result

    def __enter__(self):
        try:
            self.counter = _Counter.registry[self.name]
        except KeyError:
            self.counter = _Counter(self.name, self.print_period)
        self.t_start_us = ticks_us()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        delta = _ticks_delta(self.t_start_us)
        self.counter.record(delta)
        self.counter.print()


def _table_formatter(name, calls, total_pct, total_ms, avg_ms):
    return f"{name: 24.24} {calls: >8} {total_pct: >12} {total_ms: >14} {avg_ms: >14}"


def print_results():
    """Print summary.

    To be called at end of script.
    """
    t_total_ms = ticks_diff(ticks_us(), _t_import) / 1000

    print()
    print(f"{_BOLD}Total-Time:{_RESET} {t_total_ms:6.3f}ms")

    header = _table_formatter(
        "Name", "Calls", "Total (%)", "Total (ms)", "Average (ms)"
    )

    print(_BOLD + header + _RESET)
    print("-" * len(header))

    counters = _Counter.registry.values()
    counters = sorted(counters, key=lambda x: x.t_time_us, reverse=True)
    for counter in counters:
        t_counter_total_ms = counter.t_time_us / 1000
        print(
            _table_formatter(
                name=counter.name,
                calls=counter.n,
                total_pct=round(100 * t_counter_total_ms / t_total_ms, 2),
                total_ms=t_counter_total_ms,
                avg_ms=t_counter_total_ms / counter.n,
            )
        )
