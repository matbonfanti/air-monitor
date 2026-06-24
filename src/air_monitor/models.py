from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class Reading:
    timestamp: datetime
    room: str
    temperature_c: float | None
    humidity_rh: float | None
    absolute_humidity_g_m3: float | None
    raw_line: str | None = None

    def timestamp_utc_iso(self) -> str:
        return self.timestamp.astimezone(UTC).isoformat(timespec="seconds")
