from __future__ import annotations

import html
import re
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

import requests

from air_monitor.humidity import absolute_humidity_g_m3
from air_monitor.models import Reading

BREAK_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
TEMP_RE = re.compile(r"(-?\d+(?:[.,]\d+)?)\s*°\s*C", re.IGNORECASE)
HUMIDITY_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*%?\s*RH\b", re.IGNORECASE)


def collect_readings(
    *,
    url: str,
    rooms: Sequence[str],
    cookie: str | None = None,
    timeout_seconds: float = 10.0,
    verify_ssl: bool = True,
    timestamp: datetime | None = None,
    session: requests.Session | None = None,
) -> list[Reading]:
    status = fetch_status(
        url=url,
        cookie=cookie,
        timeout_seconds=timeout_seconds,
        verify_ssl=verify_ssl,
        session=session,
    )
    return parse_status(status, rooms=rooms, timestamp=timestamp)


def fetch_status(
    *,
    url: str,
    cookie: str | None = None,
    timeout_seconds: float = 10.0,
    verify_ssl: bool = True,
    session: requests.Session | None = None,
) -> str:
    client = session or requests.Session()
    headers = {"Cookie": cookie} if cookie else None
    response = client.get(
        url,
        headers=headers,
        timeout=timeout_seconds,
        verify=verify_ssl,
    )
    response.raise_for_status()
    return extract_status(response.json())


def extract_status(payload: Any) -> str:
    if isinstance(payload, dict):
        if "status" in payload:
            return str(payload["status"])

        devices = payload.get("list")
        if isinstance(devices, list) and devices:
            first_device = devices[0]
            if isinstance(first_device, dict) and "status" in first_device:
                return str(first_device["status"])

    msg = "Could not find device status in response payload"
    raise ValueError(msg)


def parse_status(
    status: str,
    *,
    rooms: Sequence[str],
    timestamp: datetime | None = None,
) -> list[Reading]:
    collected_at = timestamp or datetime.now(UTC)
    records = _split_records(status)

    readings = []
    for room in rooms:
        raw_line = _find_record_for_room(records, room)
        temperature_c = _extract_first_float(TEMP_RE, raw_line) if raw_line else None
        humidity_rh = _extract_first_float(HUMIDITY_RE, raw_line) if raw_line else None
        readings.append(
            Reading(
                timestamp=collected_at,
                room=room,
                temperature_c=temperature_c,
                humidity_rh=humidity_rh,
                absolute_humidity_g_m3=absolute_humidity_g_m3(temperature_c, humidity_rh),
                raw_line=raw_line,
            )
        )

    return readings


def _split_records(status: str) -> list[str]:
    return [
        html.unescape(record).strip()
        for record in BREAK_RE.split(status.replace("&deg;", "°"))
        if record.strip()
    ]


def _find_record_for_room(records: Sequence[str], room: str) -> str | None:
    wanted = room.casefold()
    for record in records:
        if wanted in record.casefold():
            return record
    return None


def _extract_first_float(pattern: re.Pattern[str], text: str) -> float | None:
    match = pattern.search(text)
    if not match:
        return None
    return float(match.group(1).replace(",", "."))
