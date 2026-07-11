from __future__ import annotations

import time


class RateLimiter:
    def __init__(self, delay_seconds: float = 3.0):
        self._delay = delay_seconds
        self._last_call: float = 0.0

    def wait(self) -> None:
        elapsed = time.monotonic() - self._last_call
        if elapsed < self._delay:
            time.sleep(self._delay - elapsed)
        self._last_call = time.monotonic()

    def reset(self) -> None:
        self._last_call = 0.0
