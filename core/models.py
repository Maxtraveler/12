from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class CheckStatus(str, Enum):
    HIT = "HIT"
    DEAD = "DEAD"
    ERROR = "ERROR"


@dataclass
class CheckResult:
    code: str
    status: CheckStatus
    discount: Optional[float] = None
    reason: Optional[str] = None
    raw: Optional[Any] = None

