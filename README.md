# Air Monitor

Small local service for collecting temperature and humidity readings from the home air device and exposing a browser dashboard.

## Development

```bash
cd /home/matteo/air-monitor
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check .
ruff format .
```

## Run Locally

```bash
AIR_DB_PATH="./readings.sqlite" air-monitor
```

The development server listens on `0.0.0.0:8000`.

## Configuration

The service is configured with environment variables:

| Variable | Default | Description |
| --- | --- | --- |
| `AIR_DEVICE_URL` | unset | Device endpoint returning the JSON payload with `list[0].status`. |
| `AIR_DEVICE_COOKIE` | unset | Optional raw cookie header, for example `PHPSESSID=...`. |
| `AIR_ROOMS` | `SOGGIORNO,CAMERA 1,CAMERA 2,CAMERA 3` | Comma-separated room names to extract from the status string. |
| `AIR_POLL_SECONDS` | `300` | Collection interval. Minimum accepted value: 10 seconds. |
| `AIR_DB_PATH` | `/data/readings.sqlite` | SQLite database path. |
| `AIR_REQUEST_TIMEOUT_SECONDS` | `10` | HTTP timeout for the device request. |
| `AIR_HOST` | `0.0.0.0` | Web server bind host. |
| `AIR_PORT` | `8000` | Web server port. |
| `AIR_STALE_AFTER_SECONDS` | `2 * AIR_POLL_SECONDS` | Mark collection as stale when no success is newer than this. |
| `AIR_ALERT_EMAIL_TO` | unset | Enable mail alerts to this recipient when collection keeps failing. |
| `AIR_ALERT_AFTER_FAILURES` | `3` | Consecutive failures before sending an alert. |
| `AIR_ALERT_COOLDOWN_SECONDS` | `21600` | Minimum seconds between repeated alerts. |
| `AIR_ALERT_COMMAND` | `mail` | Mail command used as `<command> -s <subject> <recipient>`. |
| `AIR_ALERT_SUBJECT_PREFIX` | `[AIR MONITOR]` | Prefix for alert email subjects. |

Example:

```bash
AIR_DEVICE_URL="http://192.168.1.45/d/A0001025/command.php?action=devices.list" \
AIR_DEVICE_COOKIE="PHPSESSID=..." \
AIR_DB_PATH="./readings.sqlite" \
air-monitor
```

## Endpoints

- `GET /`: dashboard
- `GET /health`: process, scheduler and database status
- `GET /api/latest`: latest reading per room
- `GET /api/readings?hours=24`: historical readings
- `POST /api/collect`: trigger one collection immediately

## Production Monitoring

`/health` returns a collection status:

- `ok`: latest collection succeeded and is recent
- `pending`: scheduler started but has not completed the first collection yet
- `error`: the last collection failed
- `stale`: no successful collection is recent enough
- `disabled`: no `AIR_DEVICE_URL` is configured

When `AIR_ALERT_EMAIL_TO` is set, the scheduler sends one email after
`AIR_ALERT_AFTER_FAILURES` consecutive failures and then waits
`AIR_ALERT_COOLDOWN_SECONDS` before sending another alert.

## Pre-Commit

The pre-commit hooks use the locally installed `ruff` binary from the development environment.

```bash
pre-commit install
pre-commit run --all-files
```
