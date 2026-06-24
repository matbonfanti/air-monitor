from __future__ import annotations

import logging
from http import HTTPStatus

from flask import Flask, jsonify, render_template_string, request

from air_monitor.config import Settings
from air_monitor.db import ReadingStore
from air_monitor.scheduler import CollectorScheduler, collect_once

DASHBOARD_HTML = """
<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Air Monitor</title>
  <style>
    :root {
      color-scheme: light dark;
      --bg: #f5f7f9;
      --fg: #17202a;
      --muted: #5f6b76;
      --line: #d8dee5;
      --panel: #ffffff;
      --accent: #1769aa;
      --good: #117a65;
      --warn: #9a5b00;
    }

    @media (prefers-color-scheme: dark) {
      :root {
        --bg: #121416;
        --fg: #eef2f4;
        --muted: #a3acb5;
        --line: #2c333a;
        --panel: #191d21;
        --accent: #63a7e6;
        --good: #53c7aa;
        --warn: #e0aa48;
      }
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      background: var(--bg);
      color: var(--fg);
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 16px;
    }

    header {
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }

    .wrap {
      width: min(1120px, calc(100% - 32px));
      margin: 0 auto;
    }

    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      min-height: 72px;
    }

    h1 {
      margin: 0;
      font-size: 22px;
      font-weight: 650;
    }

    main {
      padding: 24px 0 40px;
    }

    .toolbar {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
      color: var(--muted);
      font-size: 14px;
    }

    select,
    button {
      min-height: 36px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--panel);
      color: var(--fg);
      font: inherit;
      padding: 0 10px;
    }

    button {
      cursor: pointer;
    }

    button:hover {
      border-color: var(--accent);
    }

    .latest {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }

    .tile,
    .chart-panel {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
    }

    .tile {
      padding: 14px;
    }

    .dehumidifier-panel {
      display: grid;
      gap: 12px;
    }

    .dehumidifier-overview,
    .dehumidifier-room {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      padding: 14px;
    }

    .dehumidifier-overview {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      align-items: center;
    }

    .status-chip {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 999px;
      font-weight: 700;
      font-size: 0.95rem;
      color: white;
      background: var(--good);
    }

    .status-chip.off {
      background: #d84315;
    }

    .status-chip.hold {
      background: #f9a825;
      color: #111;
    }

    .dehumidifier-room .values {
      grid-template-columns: repeat(2, minmax(120px, 1fr));
    }

    .dehumidifier-room .stamp {
      margin-top: 12px;
      font-size: 13px;
      color: var(--muted);
    }

    .room {
      margin-bottom: 12px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
      text-transform: uppercase;
    }

    .values {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
    }

    .label {
      color: var(--muted);
      font-size: 12px;
    }

    .value {
      margin-top: 2px;
      font-size: 20px;
      font-weight: 650;
    }

    .stamp {
      margin-top: 12px;
      color: var(--muted);
      font-size: 12px;
    }

    .chart-panel {
      margin-top: 14px;
      padding: 14px;
    }

    .chart-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: baseline;
      margin-bottom: 8px;
    }

    h2 {
      margin: 0;
      font-size: 16px;
      font-weight: 650;
    }

    .hint {
      color: var(--muted);
      font-size: 13px;
    }

    svg {
      display: block;
      width: 100%;
      height: 280px;
    }

    .status-ok { color: var(--good); }
    .status-warn { color: var(--warn); }
  </style>
</head>
<body>
  <header>
    <div class="wrap topbar">
      <h1>Air Monitor</h1>
      <div class="toolbar">
        <label>
          Intervallo
          <select id="range">
            <option value="6">6 ore</option>
            <option value="24" selected>24 ore</option>
            <option value="72">3 giorni</option>
            <option value="168">7 giorni</option>
          </select>
        </label>
        <button id="collect" type="button">Raccogli ora</button>
        <span id="status">Caricamento...</span>
      </div>
    </div>
  </header>

  <main class="wrap">
    <section id="latest" class="latest"></section>

    <section class="chart-panel dehumidifier-panel">
      <div class="chart-head">
        <h2>Deumidificatore</h2>
      </div>
      <div id="dehumidifier-panel" class="dehumidifier-overview">
        Caricamento condizioni deumidificatore...
      </div>
    </section>

    <section class="chart-panel">
      <div class="chart-head">
        <h2>Temperatura</h2>
        <span class="hint">C</span>
      </div>
      <svg id="temperature-chart" role="img" aria-label="Grafico temperatura"></svg>
    </section>

    <section class="chart-panel">
      <div class="chart-head">
        <h2>Umidita relativa</h2>
        <span class="hint">RH</span>
      </div>
      <svg id="humidity-chart" role="img" aria-label="Grafico umidita relativa"></svg>
    </section>

    <section class="chart-panel">
      <div class="chart-head">
        <h2>Umidita assoluta</h2>
        <span class="hint">g/m3</span>
      </div>
      <svg id="absolute-humidity-chart" role="img" aria-label="Grafico umidita assoluta"></svg>
    </section>
  </main>

  <script>
    const colors = ["#1769aa", "#c43b3b", "#117a65", "#8a5cc2", "#b36b00", "#4f7f87"];
    const latestEl = document.getElementById("latest");
    const dehumidifierEl = document.getElementById("dehumidifier-panel");
    const statusEl = document.getElementById("status");
    const rangeEl = document.getElementById("range");
    const collectEl = document.getElementById("collect");

    function fmtNumber(value, suffix) {
      if (value === null || value === undefined) return "-";
      return `${Number(value).toFixed(1)} ${suffix}`;
    }

    function fmtTime(value) {
      if (!value) return "-";
      return new Intl.DateTimeFormat("it-IT", {
        dateStyle: "short",
        timeStyle: "short",
      }).format(new Date(value));
    }

    function setStatus(text, ok = true) {
      statusEl.textContent = text;
      statusEl.className = ok ? "status-ok" : "status-warn";
    }

    function renderLatest(readings) {
      if (!readings.length) {
        latestEl.innerHTML = '<div class="tile">Nessun dato raccolto.</div>';
        return;
      }

      latestEl.innerHTML = readings.map((reading) => `
        <article class="tile">
          <div class="room">${reading.room}</div>
          <div class="values">
            <div>
              <div class="label">Temp</div>
              <div class="value">${fmtNumber(reading.temperature_c, "C")}</div>
            </div>
            <div>
              <div class="label">RH</div>
              <div class="value">${fmtNumber(reading.humidity_rh, "%")}</div>
            </div>
            <div>
              <div class="label">AH</div>
              <div class="value">${fmtNumber(reading.absolute_humidity_g_m3, "g/m3")}</div>
            </div>
          </div>
          <div class="stamp">${fmtTime(reading.timestamp)}</div>
        </article>
      `).join("");
    }

    function renderDehumidifier(payload) {
      if (!payload || !payload.rooms || !payload.rooms.length) {
        dehumidifierEl.innerHTML = '<div class="dehumidifier-room">Nessun dato disponibile.</div>';
        return;
      }

      const statusClass = `status-chip ${payload.status}`;
      const ruleBlocks = [`
        <div>
          <div class="label">ON se RH ≥</div>
          <div class="value">${fmtNumber(payload.rules.on_rh, "%")}</div>
        </div>
        <div>
          <div class="label">Min temp</div>
          <div class="value">${fmtNumber(payload.rules.min_temp, "C")}</div>
        </div>
        <div>
          <div class="label">OFF se RH ≤</div>
          <div class="value">${fmtNumber(payload.rules.off_rh, "%")}</div>
        </div>
      `].join("");

      const rows = payload.rooms
        .map((room) => `
          <article class="dehumidifier-room">
            <div class="room">${room.room}</div>
            <div class="values">
              <div>
                <div class="label">Temp</div>
                <div class="value">${fmtNumber(room.temperature_c, "C")}</div>
              </div>
              <div>
                <div class="label">RH</div>
                <div class="value">${fmtNumber(room.humidity_rh, "%")}</div>
              </div>
              <div>
                <div class="label">Stato</div>
                <div class="value">${room.status.toUpperCase()}</div>
              </div>
            </div>
            <div class="stamp">${room.message}</div>
          </article>
        `)
        .join("");

      dehumidifierEl.innerHTML = `
        <div class="dehumidifier-overview">
          <div>
            <div class="room">Stato totale</div>
            <div class="status-chip ${payload.status}">${payload.status.toUpperCase()}</div>
          </div>
          ${ruleBlocks}
        </div>
        ${rows}
      `;
    }

    function drawChart(svgId, readings, key, emptyLabel) {
      const svg = document.getElementById(svgId);
      const width = 920;
      const height = 260;
      const pad = { top: 18, right: 18, bottom: 34, left: 42 };
      svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
      svg.innerHTML = "";

      const points = readings
        .filter((reading) => reading[key] !== null && reading[key] !== undefined)
        .map((reading) => ({
          room: reading.room,
          time: new Date(reading.timestamp).getTime(),
          value: Number(reading[key]),
        }));

      if (!points.length) {
        addText(svg, width / 2, height / 2, emptyLabel, "middle", "var(--muted)");
        return;
      }

      const minTime = Math.min(...points.map((point) => point.time));
      const maxTime = Math.max(...points.map((point) => point.time));
      const values = points.map((point) => point.value);
      const minValue = Math.floor(Math.min(...values) - 1);
      const maxValue = Math.ceil(Math.max(...values) + 1);
      const timeSpan = Math.max(maxTime - minTime, 1);
      const valueSpan = Math.max(maxValue - minValue, 1);

      const x = (time) =>
        pad.left + ((time - minTime) / timeSpan) * (width - pad.left - pad.right);
      const y = (value) =>
        height - pad.bottom
        - ((value - minValue) / valueSpan) * (height - pad.top - pad.bottom);

      drawGrid(svg, width, height, pad, minValue, maxValue);

      const byRoom = new Map();
      for (const point of points) {
        if (!byRoom.has(point.room)) byRoom.set(point.room, []);
        byRoom.get(point.room).push(point);
      }

      Array.from(byRoom.entries()).forEach(([room, roomPoints], index) => {
        roomPoints.sort((a, b) => a.time - b.time);
        const polyline = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
        polyline.setAttribute("fill", "none");
        polyline.setAttribute("stroke", colors[index % colors.length]);
        polyline.setAttribute("stroke-width", "2.5");
        const linePoints = roomPoints
          .map((point) => `${x(point.time)},${y(point.value)}`)
          .join(" ");
        polyline.setAttribute("points", linePoints);
        svg.appendChild(polyline);

        const legendX = pad.left + index * 132;
        const legendY = height - 8;
        addLine(
          svg,
          legendX,
          legendY - 4,
          legendX + 18,
          legendY - 4,
          colors[index % colors.length],
          3
        );
        addText(svg, legendX + 24, legendY, room, "start", "var(--muted)", "12px");
      });
    }

    function drawGrid(svg, width, height, pad, minValue, maxValue) {
      addLine(svg, pad.left, pad.top, pad.left, height - pad.bottom, "var(--line)", 1);
      addLine(
        svg,
        pad.left,
        height - pad.bottom,
        width - pad.right,
        height - pad.bottom,
        "var(--line)",
        1
      );

      for (let i = 0; i <= 4; i += 1) {
        const ratio = i / 4;
        const y = pad.top + ratio * (height - pad.top - pad.bottom);
        const value = maxValue - ratio * (maxValue - minValue);
        addLine(svg, pad.left, y, width - pad.right, y, "var(--line)", 0.7, "4 5");
        addText(svg, pad.left - 8, y + 4, value.toFixed(1), "end", "var(--muted)", "11px");
      }
    }

    function addLine(svg, x1, y1, x2, y2, stroke, width, dash = "") {
      const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.setAttribute("x1", x1);
      line.setAttribute("y1", y1);
      line.setAttribute("x2", x2);
      line.setAttribute("y2", y2);
      line.setAttribute("stroke", stroke);
      line.setAttribute("stroke-width", width);
      if (dash) line.setAttribute("stroke-dasharray", dash);
      svg.appendChild(line);
    }

    function addText(svg, x, y, text, anchor, fill, size = "13px") {
      const node = document.createElementNS("http://www.w3.org/2000/svg", "text");
      node.setAttribute("x", x);
      node.setAttribute("y", y);
      node.setAttribute("text-anchor", anchor);
      node.setAttribute("fill", fill);
      node.setAttribute("font-size", size);
      node.textContent = text;
      svg.appendChild(node);
    }

    async function refresh() {
      const hours = rangeEl.value;
      const [
        healthResponse,
        latestResponse,
        dehumidifierResponse,
        readingsResponse,
      ] = await Promise.all([
        fetch("/health"),
        fetch("/api/latest"),
        fetch("/api/dehumidifier-status"),
        fetch(`/api/readings?hours=${hours}`),
      ]);

      if (
        !healthResponse.ok ||
        !latestResponse.ok ||
        !dehumidifierResponse.ok ||
        !readingsResponse.ok
      ) {
        setStatus("Errore lettura dati", false);
        return;
      }

      const health = await healthResponse.json();
      const latest = await latestResponse.json();
      const history = await readingsResponse.json();
      renderLatest(latest.readings);
      drawChart(
        "temperature-chart",
        history.readings,
        "temperature_c",
        "Nessuna temperatura disponibile"
      );
      drawChart("humidity-chart", history.readings, "humidity_rh", "Nessuna umidita disponibile");
      drawChart(
        "absolute-humidity-chart",
        history.readings,
        "absolute_humidity_g_m3",
        "Nessuna umidita assoluta disponibile"
      );

      renderDehumidifier(dehumidifier);

      if (health.status === "error" || health.status === "stale") {
        const scheduler = health.scheduler || {};
        const detail = scheduler.last_error ? `: ${scheduler.last_error}` : "";
        setStatus(`${health.status}${detail}`, false);
        return;
      }

      if (health.status === "disabled" || health.status === "stopped") {
        setStatus(health.status, false);
        return;
      }

      setStatus(`${health.status} - ${new Date().toLocaleTimeString("it-IT")}`);
    }

    rangeEl.addEventListener("change", refresh);
    collectEl.addEventListener("click", async () => {
      collectEl.disabled = true;
      setStatus("Raccolta in corso...");
      const response = await fetch("/api/collect", { method: "POST" });
      collectEl.disabled = false;
      if (!response.ok) {
        const payload = await response.json();
        setStatus(payload.error || "Raccolta non riuscita", false);
        return;
      }
      refresh();
    });

    refresh();
    setInterval(refresh, 60000);
  </script>
</body>
</html>
"""


def create_app(
    settings: Settings | None = None,
    store: ReadingStore | None = None,
    *,
    start_scheduler: bool = False,
) -> Flask:
    settings = settings or Settings.from_env()
    store = store or ReadingStore(settings.db_path)
    store.initialize()

    app = Flask(__name__)
    app.extensions["air_monitor_settings"] = settings
    app.extensions["air_monitor_store"] = store

    scheduler = None
    if start_scheduler and settings.device_url:
        scheduler = CollectorScheduler(settings, store)
        scheduler.start()
    app.extensions["air_monitor_scheduler"] = scheduler

    @app.get("/")
    def dashboard():
        return render_template_string(DASHBOARD_HTML)

    @app.get("/health")
    def health():
        scheduler_status = scheduler.status() if scheduler else {"running": False}
        service_status = scheduler_status.get(
            "collection_status",
            "disabled" if not settings.device_url else "stopped",
        )
        return jsonify(
            {
                "status": service_status,
                "device_configured": bool(settings.device_url),
                "rooms": settings.rooms,
                "readings_count": store.count(),
                "scheduler": scheduler_status,
            }
        )

    @app.get("/api/latest")
    def latest():
        return jsonify({"readings": store.latest_by_room()})

    @app.get("/api/readings")
    def readings():
        hours = _parse_hours(request.args.get("hours"))
        return jsonify({"readings": store.list_readings(hours=hours)})

    @app.get("/api/dehumidifier-status")
    def dehumidifier_status():
        latest = store.latest_by_room()
        if not latest:
            return jsonify(
                {
                    "status": "unknown",
                    "message": "Nessun dato disponibile",
                    "rooms": [],
                    "rules": {
                        "on_rh": settings.dehumidifier_on_rh,
                        "min_temp": settings.dehumidifier_min_temp,
                        "off_rh": settings.dehumidifier_off_rh,
                    },
                }
            )

        rooms = []
        for reading in latest:
            humidity = reading.get("humidity_rh")
            temperature = reading.get("temperature_c")
            if humidity is None or temperature is None:
                status = "unknown"
                message = "Dati incompleti"
            elif (
                temperature >= settings.dehumidifier_min_temp
                and humidity >= settings.dehumidifier_on_rh
            ):
                status = "on"
                message = "Condizioni per accendere il deumidificatore"
            elif humidity <= settings.dehumidifier_off_rh:
                status = "off"
                message = "Condizioni per spegnere il deumidificatore"
            else:
                status = "hold"
                message = "Nessuna azione consigliata"

            rooms.append(
                {
                    "room": reading["room"],
                    "temperature_c": temperature,
                    "humidity_rh": humidity,
                    "status": status,
                    "message": message,
                }
            )

        overall = (
            "on"
            if any(room["status"] == "on" for room in rooms)
            else "off"
            if all(room["status"] in {"off", "unknown"} for room in rooms)
            else "hold"
        )

        return jsonify(
            {
                "status": overall,
                "rooms": rooms,
                "rules": {
                    "on_rh": settings.dehumidifier_on_rh,
                    "min_temp": settings.dehumidifier_min_temp,
                    "off_rh": settings.dehumidifier_off_rh,
                },
            }
        )

    @app.post("/api/collect")
    def collect():
        try:
            count = collect_once(settings, store)
        except Exception as exc:
            logging.getLogger(__name__).exception("Manual air monitor collection failed")
            return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST

        return jsonify({"inserted": count})

    return app


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = Settings.from_env()
    app = create_app(settings=settings, start_scheduler=True)

    try:
        app.run(host=settings.host, port=settings.port)
    finally:
        scheduler = app.extensions.get("air_monitor_scheduler")
        if scheduler:
            scheduler.stop()


def _parse_hours(value: str | None) -> int:
    if not value:
        return 24
    try:
        hours = int(value)
    except ValueError:
        return 24
    return max(1, min(hours, 24 * 365))


if __name__ == "__main__":
    main()
