from __future__ import annotations

import math


def absolute_humidity_g_m3(temperature_c: float | None, humidity_rh: float | None) -> float | None:
    if temperature_c is None or humidity_rh is None:
        return None

    vapor_pressure = 6.112 * math.exp((17.67 * temperature_c) / (temperature_c + 243.5))
    return (vapor_pressure * humidity_rh * 2.1674) / (273.15 + temperature_c)
