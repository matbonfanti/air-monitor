from datetime import UTC, datetime
from pathlib import Path

from air_monitor.app import create_app
from air_monitor.config import Settings
from air_monitor.db import ReadingStore
from air_monitor.models import Reading


def _test_settings(db_path: Path) -> Settings:
    return Settings(
        device_url=None,
        device_cookie=None,
        rooms=("SOGGIORNO", "CAMERA 1"),
        poll_seconds=300,
        db_path=db_path,
        request_timeout_seconds=10.0,
        verify_ssl=True,
        dehumidifier_on_rh=61.0,
        dehumidifier_min_temp=24.0,
        dehumidifier_off_rh=58.0,
        host="127.0.0.1",
        port=8000,
        stale_after_seconds=600,
        alert_after_failures=3,
        alert_cooldown_seconds=21_600,
        alert_email_to=None,
        alert_command="mail",
        alert_subject_prefix="[AIR MONITOR]",
    )


def test_health_endpoint_returns_ok(tmp_path):
    db_path = tmp_path / "readings.sqlite"
    app = create_app(settings=_test_settings(db_path), store=ReadingStore(db_path))
    client = app.test_client()

    response = client.get("/health")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "disabled"
    assert payload["device_configured"] is False


def test_dashboard_endpoint_returns_html(tmp_path):
    app = create_app(settings=_test_settings(tmp_path / "readings.sqlite"))
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"Air Monitor" in response.data


def test_dehumidifier_status_endpoint_reports_rules_and_room_states(tmp_path):
    db_path = tmp_path / "readings.sqlite"
    store = ReadingStore(db_path)
    store.initialize()
    store.add_readings(
        [
            Reading(
                timestamp=datetime.now(UTC),
                room="SOGGIORNO",
                temperature_c=25.0,
                humidity_rh=62.0,
                absolute_humidity_g_m3=12.0,
                raw_line=None,
            ),
            Reading(
                timestamp=datetime.now(UTC),
                room="CAMERA 1",
                temperature_c=22.0,
                humidity_rh=56.0,
                absolute_humidity_g_m3=10.8,
                raw_line=None,
            ),
        ]
    )
    app = create_app(settings=_test_settings(db_path), store=store)
    client = app.test_client()

    response = client.get("/api/dehumidifier-status")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] in {"on", "off", "hold"}
    assert payload["rules"]["on_rh"] == 61.0
    assert payload["rules"]["min_temp"] == 24.0
    assert payload["rules"]["off_rh"] == 58.0
    assert any(room["room"] == "SOGGIORNO" and room["status"] == "on" for room in payload["rooms"])
    assert any(room["room"] == "CAMERA 1" for room in payload["rooms"])
