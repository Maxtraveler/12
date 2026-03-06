from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator, Iterable, Iterator, Protocol


ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


class PromoCodeSource(Protocol):
    def __aiter__(self) -> AsyncIterator[str]:  # pragma: no cover - protocol definition
        ...


def _generate_by_mask_sync(mask: str) -> Iterator[str]:
    """
    Синхронный генератор всех промокодов по маске.

    Поддерживается символ 'X' как любая буква/цифра из ALPHABET.
    Остальные символы маски считаются фиксированными.
    """
    if not mask:
        return

    indices = [0] * len(mask)
    max_indices = [len(ALPHABET) - 1 if ch == "X" else 0 for ch in mask]

    def build_code() -> str:
        chars = []
        for ch, idx, max_idx in zip(mask, indices, max_indices):
            if max_idx == 0 and ch != "X":
                chars.append(ch)
            else:
                chars.append(ALPHABET[idx])
        return "".join(chars)

    # Первая комбинация
    yield build_code()

    while True:
        carry = 1
        for pos in range(len(indices) - 1, -1, -1):
            if max_indices[pos] == 0 and mask[pos] != "X":
                continue
            if carry == 0:
                break
            indices[pos] += carry
            if indices[pos] > max_indices[pos]:
                indices[pos] = 0
                carry = 1
            else:
                carry = 0
        if carry == 1:
            break
        yield build_code()


async def generate_by_mask(mask: str) -> AsyncIterator[str]:
    """
    Асинхронный обёртка над генерацией по маске.

    Сделана асинхронной, чтобы можно было при желании вставлять небольшие паузы
    и не блокировать event loop при больших переборах.
    """
    loop = asyncio.get_running_loop()

    for code in _generate_by_mask_sync(mask):
        # При очень больших масках можно периодически уступать управление циклу.
        await asyncio.sleep(0)
        yield code


async def iter_from_file(path: str | Path, encoding: str = "utf-8") -> AsyncIterator[str]:
    """
    Асинхронное чтение промокодов из файла, по одному коду на строку.
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(file_path)

    # Читаем построчно в отдельном потоке, чтобы не блокировать event loop.
    def _read_lines() -> Iterable[str]:
        with file_path.open("r", encoding=encoding) as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    yield stripped

    loop = asyncio.get_running_loop()
    for line in await loop.run_in_executor(None, lambda: list(_read_lines())):
        yield line


async def single_code(code: str) -> AsyncIterator[str]:
    """
    Асинхронный источник, который выдаёт один конкретный промокод.
    """
    yield code


@dataclass
class MaskSource:
    mask: str

    def __aiter__(self) -> AsyncIterator[str]:
        return generate_by_mask(self.mask)


@dataclass
class FileSource:
    path: Path

    def __aiter__(self) -> AsyncIterator[str]:
        return iter_from_file(self.path)


@dataclass
class SingleCodeSource:
    code: str

    def __aiter__(self) -> AsyncIterator[str]:
        return single_code(self.code)

