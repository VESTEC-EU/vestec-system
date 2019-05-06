from mproxy.server import throttle
import pytest


class MonkeyClock:
    """Time only advances by the amount of sleeping done"""

    import time

    def __init__(self, monkeypatch=None):
        self.now_ns = 0
        if monkeypatch is not None:
            self.patch(monkeypatch)
        self._expect = None

    def advance_ns(self, ns):
        self.now_ns += ns

    def advance_ms(self, ms):
        self.now_ns += ms * 1000 ** 2

    def monotonic_ns(self):
        return self.now_ns

    def sleep(self, how_long_s):
        how_long_ns = int(how_long_s * 1e9)
        if self._expect is not None:
            assert how_long_ns == self._expect
            self._expect = None

        self.now_ns += how_long_ns
        return

    def expect_sleep_ms(self, ms):
        self._expect = ms * 1000000

    def sleep_is_error(self):
        del self._expect

    def sleep_is_free(self):
        self._expect = None

    def patch(self, monkeypatch):
        monkeypatch.setattr(self.time, "sleep", self.sleep)
        monkeypatch.setattr(self.time, "monotonic_ns", self.monotonic_ns)

    pass


def test_monkey_clock():
    c = MonkeyClock()
    assert c.monotonic_ns() == 0
    c.sleep(1e-6)
    assert c.monotonic_ns() == 1000
    c.expect_sleep_ms(2)
    c.sleep(2e-3)
    assert c.monotonic_ns() == 2001000
    with pytest.raises(AssertionError):
        c.expect_sleep_ms(1)
        c.sleep(2e-3)


def test_hammering_ramps_up_wait(monkeypatch):
    clk = MonkeyClock(monkeypatch)

    thr = throttle.Throttle(1, 64)
    # We start up and keep hammering
    sleep = 1
    # No sleep first time around
    clk.sleep_is_error()
    for i in range(20):
        thr()
        # sleep 1ms second iteration, doubling up to the limit on
        # subsequent iterations
        clk.expect_sleep_ms(sleep)
        sleep = min(2 * sleep, 64)


def test_post_hammer_backoff(monkeypatch):
    clk = MonkeyClock(monkeypatch)
    thr = throttle.Throttle(1, 64)
    # Set to maxed out
    thr.cur_wait = 64
    thr.t_last_ns = clk.now_ns

    # test the back off - we are retrying after more than the current
    # required wait
    clk.advance_ms(65)
    clk.sleep_is_error()
    thr()
    assert thr.cur_wait == 32
    clk.advance_ms(49)
    thr()
    assert thr.cur_wait == 8
    clk.advance_ms(1000)
    thr()
    assert thr.cur_wait == 1


def test_steady_event_rate(monkeypatch):
    clk = MonkeyClock(monkeypatch)
    thr = throttle.Throttle(1, 64)

    # Holding in the middle of our range
    thr.cur_wait = 8
    thr.t_last_ns = clk.now_ns

    for i in range(10):
        # have events occur at halfway almost up to the whole way
        # through the wait period
        clk.sleep(4e-3 + 4e-4 * i)
        thr()
        assert thr.cur_wait == 8
        assert clk.now_ns == (i + 1) * 8 * 1000 * 1000


def test_post_hammer_long_pause_resets(monkeypatch):
    clk = MonkeyClock(monkeypatch)
    thr = throttle.Throttle(1, 64)

    # Set to maxed out
    thr.cur_wait = 64
    thr.t_last_ns = clk.now_ns

    # Now a big pause
    clk.advance_ms(10000)
    clk.sleep_is_error()
    thr()
    assert thr.cur_wait == thr.min_wait
