from datetime import UTC, datetime

from air_monitor.collector import extract_status, fetch_status, parse_status
from air_monitor.config import Settings


def test_extract_status_from_device_list_payload():
    payload = {"list": [{"status": "SOGGIORNO 21.5 &deg;C 55 RH"}]}

    assert extract_status(payload) == "SOGGIORNO 21.5 &deg;C 55 RH"


def test_parse_status_extracts_first_temperature_and_humidity():
    timestamp = datetime(2026, 6, 24, 20, 30, tzinfo=UTC)
    status = (
        "SOGGIORNO aria 21,5 &deg;C soglia 35 °C 54 RH<br>CAMERA 1 aria 19.0 °C soglia 35 °C 60 RH"
    )

    readings = parse_status(
        status,
        rooms=("SOGGIORNO", "CAMERA 1", "CAMERA 2"),
        timestamp=timestamp,
    )

    assert readings[0].room == "SOGGIORNO"
    assert readings[0].temperature_c == 21.5
    assert readings[0].humidity_rh == 54
    assert readings[0].absolute_humidity_g_m3 is not None
    assert readings[0].raw_line == "SOGGIORNO aria 21,5 °C soglia 35 °C 54 RH"
    assert readings[1].temperature_c == 19.0
    assert readings[1].humidity_rh == 60
    assert readings[2].temperature_c is None
    assert readings[2].humidity_rh is None


def test_fetch_status_disables_ssl_verification(monkeypatch):
    class DummyResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, list[dict[str, str]]]:
            return {"list": [{"status": "SOGGIORNO 20 C 50 RH"}]}

    class DummySession:
        def get(self, url: str, headers: dict[str, str] | None, timeout: float, verify: bool):
            assert url == "https://example.local/device-status"
            assert headers == {"Cookie": "PHPSESSID=test-session"}
            assert timeout == 1
            assert verify is False
            return DummyResponse()

    monkeypatch.setattr("air_monitor.collector.requests.Session", lambda: DummySession())

    status = fetch_status(
        url="https://example.local/device-status",
        cookie="PHPSESSID=test-session",
        timeout_seconds=1,
        verify_ssl=False,
    )

    assert status == "SOGGIORNO 20 C 50 RH"


def test_settings_from_env_disables_ssl_verification():
    settings = Settings.from_env({"AIR_DEVICE_VERIFY_SSL": "false"})

    assert settings.verify_ssl is False
