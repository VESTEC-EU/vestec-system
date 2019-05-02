import time
from functools import wraps

class Throttle:
    def __init__(self, min_wait_ms, max_wait_ms):
        # in nanoseconds
        self.scale_ns = 1000000

        # in multiples of self.scale
        self.min_wait = min_wait_ms
        self.max_wait = max_wait_ms
        self.cur_wait = self.min_wait

        # In ns
        self.t_last = time.monotonic_ns()

    def __call__(self):
        '''Pause to control waiting'''
        now = time.monotonic_ns()
        ok_after = self.t_last + (self.cur_wait * self.scale_ns)
        if now < ok_after:
            # We are in the forbidden zone must sleep until we're OK
            # and the wait period doubles (up to the limit)
            time.sleep((ok_after - now) * 1e-9)
            self.cur_wait = min(self.cur_wait * 2, self.max_wait)
        else:
            # We are ok, reduce the wait period (up to the limit)
            self.cur_wait = max(self.cur_wait / 2, self.min_wait)
    pass

class NoThrottle:
    def __init__(self, *args, **kwargs):
        pass
    def __call__(self):
        return
    pass


def throttle(func_or_attr):
    '''Decorator to annotate methods as needing rate-limited'''
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        thr = self._throttle
        thr()
        return func(self, *args, **kwargs)
    return wrapper

class ThrottableMixin:
    def __init__(self, min_wait_ms, max_wait_ms):
        if min_wait:
            self._throttle = Throttle(min_wait_ms, max_wait_ms)
        else:
            self._throttle = NoThrottle()
