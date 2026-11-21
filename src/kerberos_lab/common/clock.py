"""Injectable wall clocks; elapsed-time measurement is a caller concern."""

import math
import time
from typing import Protocol

from ._validation import MAX_INTEGER, integer


class Clock(Protocol):
    def now(self) -> int: ...


class SystemClock:
    def now(self) -> int:
        return integer(math.floor(time.time()))


class FrozenClock:
    def __init__(self, timestamp: int) -> None:
        self.set(timestamp)

    def now(self) -> int:
        return self._timestamp

    def set(self, timestamp: int) -> None:
        self._timestamp = integer(timestamp)

    def advance(self, seconds: int) -> None:
        integer(seconds, minimum=-MAX_INTEGER)
        self.set(self._timestamp + seconds)


class OffsetClock:
    def __init__(self, base: Clock, offset_seconds: int) -> None:
        self._base = base
        self._offset = integer(offset_seconds, minimum=-MAX_INTEGER)

    def now(self) -> int:
        return integer(integer(self._base.now()) + self._offset)
