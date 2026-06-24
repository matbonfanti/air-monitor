from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ROOMS = ("SOGGIORNO", "CAMERA 1", "CAMERA 2", "CAMERA 3")


@dataclass(frozen=True)
class Settings:
    device_url: str | None
    device_cookie: str | None
    rooms: tuple[str, ...]
    poll_seconds: int
    db_path: Path
    request_timeout_seconds: float
    host: str
    port: int
    stale_after_seconds: int
    alert_after_failures: int
    alert_cooldown_seconds: int
    alert_email_to: str | None
    alert_command: str
    alert_subject_prefix: str

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        env = environ or os.environ
        poll_seconds = _parse_int(env.get("AIR_POLL_SECONDS"), default=300, minimum=10)
        return cls(
            device_url=_blank_to_none(env.get("AIR_DEVICE_URL")),
            device_cookie=_blank_to_none(env.get("AIR_DEVICE_COOKIE")),
            rooms=_parse_rooms(env.get("AIR_ROOMS")),
            poll_seconds=poll_seconds,
            db_path=Path(env.get("AIR_DB_PATH", "/data/readings.sqlite")),
            request_timeout_seconds=_parse_float(
                env.get("AIR_REQUEST_TIMEOUT_SECONDS"), default=10.0, minimum=1.0
            ),
            host=env.get("AIR_HOST", "0.0.0.0"),
            port=_parse_int(env.get("AIR_PORT"), default=8000, minimum=1),
            stale_after_seconds=_parse_int(
                env.get("AIR_STALE_AFTER_SECONDS"),
                default=poll_seconds * 2,
                minimum=poll_seconds,
            ),
            alert_after_failures=_parse_int(
                env.get("AIR_ALERT_AFTER_FAILURES"),
                default=3,
                minimum=1,
            ),
            alert_cooldown_seconds=_parse_int(
                env.get("AIR_ALERT_COOLDOWN_SECONDS"),
                default=21_600,
                minimum=60,
            ),
            alert_email_to=_blank_to_none(env.get("AIR_ALERT_EMAIL_TO")),
            alert_command=env.get("AIR_ALERT_COMMAND", "mail"),
            alert_subject_prefix=env.get("AIR_ALERT_SUBJECT_PREFIX", "[AIR MONITOR]"),
        )


def _blank_to_none(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    return value.strip()


def _parse_rooms(value: str | None) -> tuple[str, ...]:
    if not value:
        return DEFAULT_ROOMS

    rooms = tuple(room.strip() for room in value.split(",") if room.strip())
    if not rooms:
        msg = "AIR_ROOMS must contain at least one room name"
        raise ValueError(msg)
    return rooms


def _parse_int(value: str | None, *, default: int, minimum: int) -> int:
    if value is None or not value.strip():
        return default

    parsed = int(value)
    if parsed < minimum:
        msg = f"Value must be >= {minimum}"
        raise ValueError(msg)
    return parsed


def _parse_float(value: str | None, *, default: float, minimum: float) -> float:
    if value is None or not value.strip():
        return default

    parsed = float(value)
    if parsed < minimum:
        msg = f"Value must be >= {minimum}"
        raise ValueError(msg)
    return parsed
