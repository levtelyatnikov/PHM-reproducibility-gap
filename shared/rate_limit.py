from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class RateLimiter:
    min_interval_seconds: float = 0.0
    clock: Callable[[], float] = time.monotonic
    sleeper: Callable[[float], None] = time.sleep
    _last_call_at: float | None = field(default=None, init=False)

    def acquire(self) -> float:
        if self.min_interval_seconds <= 0:
            self._last_call_at = self.clock()
            return 0.0
        now = self.clock()
        if self._last_call_at is None:
            self._last_call_at = now
            return 0.0
        elapsed = now - self._last_call_at
        if elapsed < self.min_interval_seconds:
            remaining = self.min_interval_seconds - elapsed
            self.sleeper(remaining)
            self._last_call_at = self.clock()
            return remaining
        self._last_call_at = now
        return 0.0

    def wait(self) -> None:
        self.acquire()
