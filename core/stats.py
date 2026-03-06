from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass
class StatsSnapshot:
    checked: int
    hits: int
    dead: int
    errors: int

    @property
    def success_rate(self) -> float:
        if self.checked == 0:
            return 0.0
        return (self.hits / self.checked) * 100.0


class Stats:
    def __init__(self) -> None:
        self._checked = 0
        self._hits = 0
        self._dead = 0
        self._errors = 0
        self._lock = asyncio.Lock()

    async def inc_checked(self, *, hits: bool = False, dead: bool = False, error: bool = False) -> None:
        async with self._lock:
            self._checked += 1
            if hits:
                self._hits += 1
            if dead:
                self._dead += 1
            if error:
                self._errors += 1

    async def snapshot(self) -> StatsSnapshot:
        async with self._lock:
            return StatsSnapshot(
                checked=self._checked,
                hits=self._hits,
                dead=self._dead,
                errors=self._errors,
            )

