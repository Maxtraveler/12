from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from aiogram import Bot

from core import Settings
from core.checker_engine import PromoChecker
from core.models import CheckStatus
from core.promocode_source import FileSource, MaskSource, SingleCodeSource
from core.stats import Stats

from .notifier import notify_dead, notify_hit, notify_stats


@dataclass
class BackgroundRunner:
    bot: Bot
    owner_id: int
    settings: Settings
    stats: Stats

    def __post_init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self._stop_event: Optional[asyncio.Event] = None

    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def stop(self) -> None:
        if self._stop_event is not None:
            self._stop_event.set()
        if self._task is not None:
            await self._task

    async def start_with_mask(self, mask: str) -> None:
        source = MaskSource(mask)
        await self._start(source.__aiter__())

    async def start_with_file(self, path: Path) -> None:
        source = FileSource(path)
        await self._start(source.__aiter__())

    async def start_with_single_code(self, code: str) -> None:
        source = SingleCodeSource(code)
        await self._start(source.__aiter__())

    async def _start(self, source) -> None:
        if self.is_running():
            await self.stop()

        self._stop_event = asyncio.Event()
        checker = PromoChecker(
            settings=self.settings,
            stats=self.stats,
            on_result=self._on_result,
            on_stats=self._on_stats,
        )

        async def _runner() -> None:
            await checker.start(source, stop_event=self._stop_event)

        self._task = asyncio.create_task(_runner())

    async def _on_result(self, result) -> None:
        if result.status is CheckStatus.HIT:
            await notify_hit(self.bot, self.owner_id, result.code, result.discount)
        elif result.status is CheckStatus.DEAD:
            await notify_dead(self.bot, self.owner_id, result.code, result.reason)
        else:
            # Ошибки можно логировать, а при частых ошибках — уведомлять отдельно.
            pass

    async def _on_stats(self, snapshot) -> None:
        await notify_stats(self.bot, self.owner_id, snapshot)

