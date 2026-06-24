from datetime import UTC, datetime

from air_monitor.collector import extract_status, parse_status


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
