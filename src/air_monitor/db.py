from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path

from air_monitor.models import Reading

SCHEMA = """
CREATE TABLE IF NOT EXISTS readings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp TEXT NOT NULL,
  room TEXT NOT NULL,
  temperature_c REAL,
  humidity_rh REAL,
  absolute_humidity_g_m3 REAL,
  raw_line TEXT
);

CREATE INDEX IF NOT EXISTS idx_readings_timestamp ON readings(timestamp);
CREATE INDEX IF NOT EXISTS idx_readings_room_timestamp ON readings(room, timestamp);
"""


class ReadingStore:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(SCHEMA)

    def add_readings(self, readings: Sequence[Reading]) -> int:
        if not readings:
            return 0

        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO readings (
                  timestamp,
                  room,
                  temperature_c,
                  humidity_rh,
                  absolute_humidity_g_m3,
                  raw_line
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        reading.timestamp_utc_iso(),
                        reading.room,
                        reading.temperature_c,
                        reading.humidity_rh,
                        reading.absolute_humidity_g_m3,
                        reading.raw_line,
                    )
                    for reading in readings
                ],
            )
        return len(readings)

    def list_readings(self, *, hours: int = 24) -> list[dict[str, object]]:
        since = datetime.now(UTC) - timedelta(hours=max(hours, 1))
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT timestamp, room, temperature_c, humidity_rh, absolute_humidity_g_m3
                FROM readings
                WHERE timestamp >= ?
                ORDER BY timestamp ASC, room ASC
                """,
                (since.isoformat(timespec="seconds"),),
            ).fetchall()
        return [_row_to_dict(row) for row in rows]

    def latest_by_room(self) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT r.timestamp,
                       r.room,
                       r.temperature_c,
                       r.humidity_rh,
                       r.absolute_humidity_g_m3
                FROM readings r
                JOIN (
                  SELECT room, MAX(id) AS id
                  FROM readings
                  GROUP BY room
                ) latest
                  ON latest.id = r.id
                ORDER BY r.room ASC
                """
            ).fetchall()
        return [_row_to_dict(row) for row in rows]

    def count(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM readings").fetchone()
        return int(row["count"])

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection


def _row_to_dict(row: sqlite3.Row) -> dict[str, object]:
    return {
        "timestamp": row["timestamp"],
        "room": row["room"],
        "temperature_c": _round_or_none(row["temperature_c"]),
        "humidity_rh": _round_or_none(row["humidity_rh"]),
        "absolute_humidity_g_m3": _round_or_none(row["absolute_humidity_g_m3"]),
    }


def _round_or_none(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 2)
