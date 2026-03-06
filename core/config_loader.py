import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


@dataclass
class Settings:
    bot_token: str
    owner_id: int
    target_url: str
    request_delay_min: float = 0.5
    request_delay_max: float = 2.0


def load_settings(env_file: Optional[str] = ".env") -> Settings:
    if env_file is not None:
        load_dotenv(env_file)

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    owner_id_raw = os.getenv("OWNER_ID", "").strip()
    target_url = os.getenv("TARGET_URL", "").strip()

    if not bot_token:
        raise RuntimeError("BOT_TOKEN is not set in environment/.env")
    if not owner_id_raw:
        raise RuntimeError("OWNER_ID is not set in environment/.env")
    if not target_url:
        raise RuntimeError("TARGET_URL is not set in environment/.env")

    try:
        owner_id = int(owner_id_raw)
    except ValueError as exc:
        raise RuntimeError("OWNER_ID must be an integer") from exc

    delay_min = float(os.getenv("REQUEST_DELAY_MIN", "0.5"))
    delay_max = float(os.getenv("REQUEST_DELAY_MAX", "2.0"))

    if delay_min <= 0 or delay_max <= 0 or delay_min > delay_max:
        raise RuntimeError("Invalid delay range in REQUEST_DELAY_MIN/MAX")

    return Settings(
        bot_token=bot_token,
        owner_id=owner_id,
        target_url=target_url,
        request_delay_min=delay_min,
        request_delay_max=delay_max,
    )

