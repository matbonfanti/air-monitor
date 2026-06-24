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
air-monitor
```

The development server listens on `0.0.0.0:8000`.

## Pre-Commit

The pre-commit hooks use the locally installed `ruff` binary from the development environment.

```bash
pre-commit install
pre-commit run --all-files
```
