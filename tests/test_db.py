from datetime import UTC, datetime

from air_monitor.db import ReadingStore
from air_monitor.models import Reading


def test_store_adds_and_reads_readings(tmp_path):
    store = ReadingStore(tmp_path / "readings.sqlite")
    store.initialize()
    timestamp = datetime(2026, 6, 24, 20, 30, tzinfo=UTC)

    inserted = store.add_readings(
        [
            Reading(timestamp, "SOGGIORNO", 21.5, 54, 10.12, "raw soggiorno"),
            Reading(timestamp, "CAMERA 1", 19.0, 60, 9.81, "raw camera"),
        ]
    )

    assert inserted == 2
    assert store.count() == 2
    assert store.latest_by_room() == [
        {
            "timestamp": "2026-06-24T20:30:00+00:00",
            "room": "CAMERA 1",
            "temperature_c": 19.0,
            "humidity_rh": 60.0,
            "absolute_humidity_g_m3": 9.81,
        },
        {
            "timestamp": "2026-06-24T20:30:00+00:00",
            "room": "SOGGIORNO",
            "temperature_c": 21.5,
            "humidity_rh": 54.0,
            "absolute_humidity_g_m3": 10.12,
        },
    ]


def test_latest_by_room_uses_last_insert_when_timestamp_matches(tmp_path):
    store = ReadingStore(tmp_path / "readings.sqlite")
    store.initialize()
    timestamp = datetime(2026, 6, 24, 20, 30, tzinfo=UTC)

    store.add_readings(
        [
            Reading(timestamp, "SOGGIORNO", 21.0, 50, 9.1, "first"),
            Reading(timestamp, "SOGGIORNO", 22.0, 51, 9.8, "second"),
        ]
    )

    assert store.latest_by_room() == [
        {
            "timestamp": "2026-06-24T20:30:00+00:00",
            "room": "SOGGIORNO",
            "temperature_c": 22.0,
            "humidity_rh": 51.0,
            "absolute_humidity_g_m3": 9.8,
        }
    ]
