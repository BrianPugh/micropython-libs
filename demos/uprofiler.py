from time import sleep

import uprofiler


@uprofiler.profile
def foo():
    sleep(0.25)


@uprofiler.profile(name="changed_bar_name")
def bar():
    sleep(0.6)


@uprofiler.profile(print_period=3)
def baz():
    sleep(0.1)


foo()

bar()
bar()

baz()
baz()
baz()
baz()
baz()
baz()

with uprofiler.profile(name="context manager demo"):
    sleep(0.123)

uprofiler.print_results()
