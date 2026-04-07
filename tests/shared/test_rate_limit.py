from __future__ import annotations

import unittest

from shared.rate_limit import RateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class RateLimiterTests(unittest.TestCase):
    def test_acquire_sleeps_until_minimum_interval_elapses(self) -> None:
        clock = FakeClock()
        sleeps: list[float] = []

        def sleeper(seconds: float) -> None:
            sleeps.append(seconds)
            clock.now += seconds

        limiter = RateLimiter(min_interval_seconds=2.0, clock=clock, sleeper=sleeper)

        self.assertEqual(limiter.acquire(), 0.0)
        clock.now = 0.5
        self.assertEqual(limiter.acquire(), 1.5)
        self.assertEqual(sleeps, [1.5])


if __name__ == "__main__":
    unittest.main()

