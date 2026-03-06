from __future__ import annotations

import asyncio
import json
import logging
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator, Awaitable, Callable, Optional

import aiohttp

from .config_loader import Settings
from .models import CheckResult, CheckStatus
from .stats import Stats


logger = logging.getLogger("promo_checker")


def setup_logging(log_dir: Path | str = "logs") -> None:
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    file_path = log_path / "checker.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.FileHandler(file_path, encoding="utf-8"), logging.StreamHandler()],
    )


OnResultCallback = Callable[[CheckResult], Awaitable[None]]
OnStatsCallback = Callable[[Any], Awaitable[None]]


@dataclass
class PromoChecker:
    settings: Settings
    stats: Stats
    on_result: Optional[OnResultCallback] = None
    on_stats: Optional[OnStatsCallback] = None
    stats_interval: float = 15.0
    concurrent_limit: int = 1
    hits_file: Path = Path("hits.txt")

    async def _send_request(self, session: aiohttp.ClientSession, code: str) -> CheckResult:
        """
        Отправка HTTP-запроса для проверки одного промокода.

        ВАЖНО: структуру payload и анализ ответа нужно адаптировать под реальный
        запрос, который вы снимете через DevTools.
        """
        payload: dict[str, Any] = {
            "promocode": code,
        }

        try:
            async with session.post(self.settings.target_url, json=payload) as resp:
                text = await resp.text()
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.error("Request failed for code %s: %s", code, exc)
            await self.stats.inc_checked(error=True)
            return CheckResult(code=code, status=CheckStatus.ERROR, reason=str(exc))

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = {"raw": text}

        # Здесь нужно подстроиться под реальные ключи в ответе «Пятёрочки».
        # Ниже — примерная логика.
        status = CheckStatus.DEAD
        discount: float | None = None
        reason: str | None = None

        success = bool(data.get("success")) or data.get("status") in {"ok", "success"}
        if success:
            status = CheckStatus.HIT
            # Попытка вытащить размер скидки
            discount_val = data.get("discount") or data.get("amount") or data.get("value")
            try:
                if discount_val is not None:
                    discount = float(discount_val)
            except (TypeError, ValueError):
                discount = None
        else:
            status = CheckStatus.DEAD
            reason = (
                data.get("error")
                or data.get("message")
                or data.get("detail")
                or "Промокод не прошёл проверку"
            )

        # Примитивная проверка на блокировку / капчу по тексту
        text_all = json.dumps(data, ensure_ascii=False).lower()
        if any(key in text_all for key in ["captcha", "капча", "too many requests", "rate limit", "blocked"]):
            status = CheckStatus.ERROR
            reason = "Возможна блокировка или капча"

        is_hit = status is CheckStatus.HIT
        is_dead = status is CheckStatus.DEAD
        is_error = status is CheckStatus.ERROR
        await self.stats.inc_checked(hits=is_hit, dead=is_dead, error=is_error)

        result = CheckResult(code=code, status=status, discount=discount, reason=reason, raw=data)

        if is_hit:
            await self._write_hit(result)

        return result

    async def _write_hit(self, result: CheckResult) -> None:
        self.hits_file.parent.mkdir(parents=True, exist_ok=True)
        line = f"{datetime.now().isoformat()} | {result.code} | discount={result.discount!r}\n"
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._append_line, self.hits_file, line)

    @staticmethod
    def _append_line(path: Path, line: str) -> None:
        with path.open("a", encoding="utf-8") as f:
            f.write(line)

    async def start(self, source: AsyncIterator[str], stop_event: Optional[asyncio.Event] = None) -> None:
        """
        Запуск проверки последовательности промокодов.

        Параметр stop_event позволяет остановить перебор снаружи.
        """
        if stop_event is None:
            stop_event = asyncio.Event()

        setup_logging()

        connector = aiohttp.TCPConnector(limit=self.concurrent_limit)
        async with aiohttp.ClientSession(connector=connector) as session:
            last_stats_report = asyncio.get_running_loop().time()

            async for code in source:
                if stop_event.is_set():
                    logger.info("Stop event received, finishing checks")
                    break

                result = await self._send_request(session, code)
                logger.info("Checked code %s: %s", code, result.status.value)

                if self.on_result is not None:
                    await self.on_result(result)

                now = asyncio.get_running_loop().time()
                if self.on_stats is not None and now - last_stats_report >= self.stats_interval:
                    last_stats_report = now
                    stats_snapshot = await self.stats.snapshot()
                    await self.on_stats(stats_snapshot)

                await asyncio.sleep(random.uniform(self.settings.request_delay_min, self.settings.request_delay_max))

