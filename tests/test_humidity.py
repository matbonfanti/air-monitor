from air_monitor.humidity import absolute_humidity_g_m3


def test_absolute_humidity_returns_none_for_missing_values():
    assert absolute_humidity_g_m3(None, 50) is None
    assert absolute_humidity_g_m3(20, None) is None


def test_absolute_humidity_calculation():
    assert round(absolute_humidity_g_m3(20, 50), 2) == 8.64
