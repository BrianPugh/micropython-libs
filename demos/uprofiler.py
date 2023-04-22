from time import sleep

import uprofiler


class MyClass:
    @uprofiler.profile
    def foo_method(self):
        sleep(0.05)


@uprofiler.profile
def foo():
    sleep(0.25)


@uprofiler.profile(name="changed_bar_name")
def bar():
    sleep(0.6)


@uprofiler.profile(print_period=3)
def baz():
    sleep(0.1)


MyClass().foo_method()

foo()

bar()
bar()

baz()
baz()
baz()
baz()
baz()
baz()

uprofiler.print_results()
