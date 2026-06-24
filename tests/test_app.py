from pathlib import Path

from air_monitor.app import create_app
from air_monitor.config import Settings
from air_monitor.db import ReadingStore


def _test_settings(db_path: Path) -> Settings:
    return Settings(
        device_url=None,
        device_cookie=None,
        rooms=("SOGGIORNO", "CAMERA 1"),
        poll_seconds=300,
        db_path=db_path,
        request_timeout_seconds=10.0,
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
