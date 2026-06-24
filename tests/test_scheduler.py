from pathlib import Path

from air_monitor.config import Settings
from air_monitor.db import ReadingStore
from air_monitor.scheduler import CollectorScheduler


class FakeNotifier:
    def __init__(self) -> None:
        self.statuses: list[dict[str, object]] = []

    def send_failure_alert(self, status: dict[str, object]) -> None:
        self.statuses.append(status)


def _settings(
    db_path: Path,
    *,
    alert_email_to: str | None = None,
    alert_after_failures: int = 2,
) -> Settings:
    return Settings(
        device_url="http://example.test/device",
        device_cookie="PHPSESSID=test",
        rooms=("SOGGIORNO",),
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
        alert_after_failures=alert_after_failures,
        alert_cooldown_seconds=21_600,
        alert_email_to=alert_email_to,
        alert_command="mail",
        alert_subject_prefix="[AIR MONITOR]",
    )


def _store(db_path: Path) -> ReadingStore:
    store = ReadingStore(db_path)
    store.initialize()
    return store


def test_scheduler_records_failure_status(monkeypatch, tmp_path):
    settings = _settings(tmp_path / "readings.sqlite")
    scheduler = CollectorScheduler(settings, _store(settings.db_path))

    def fail_collect(settings, store):
        raise RuntimeError("expired cookie")

    monkeypatch.setattr("air_monitor.scheduler.collect_once", fail_collect)

    scheduler._collect_and_record_status()

    status = scheduler.status()
    assert status["collection_status"] == "error"
    assert status["consecutive_failures"] == 1
    assert status["last_error"] == "expired cookie"


def test_scheduler_sends_alert_after_threshold_and_respects_cooldown(monkeypatch, tmp_path):
    settings = _settings(tmp_path / "readings.sqlite", alert_email_to="matteo@example.test")
    notifier = FakeNotifier()
    scheduler = CollectorScheduler(settings, _store(settings.db_path), notifier=notifier)

    def fail_collect(settings, store):
        raise RuntimeError("expired cookie")

    monkeypatch.setattr("air_monitor.scheduler.collect_once", fail_collect)

    scheduler._collect_and_record_status()
    scheduler._collect_and_record_status()
    scheduler._collect_and_record_status()

    assert len(notifier.statuses) == 1
    assert notifier.statuses[0]["collection_status"] == "error"
    assert notifier.statuses[0]["consecutive_failures"] == 2
    assert scheduler.status()["consecutive_failures"] == 3


def test_scheduler_resets_failure_count_after_success(monkeypatch, tmp_path):
    settings = _settings(tmp_path / "readings.sqlite")
    scheduler = CollectorScheduler(settings, _store(settings.db_path))

    def fail_collect(settings, store):
        raise RuntimeError("expired cookie")

    monkeypatch.setattr("air_monitor.scheduler.collect_once", fail_collect)
    scheduler._collect_and_record_status()

    def succeed_collect(settings, store):
        return 0

    monkeypatch.setattr("air_monitor.scheduler.collect_once", succeed_collect)
    scheduler._collect_and_record_status()

    status = scheduler.status()
    assert status["collection_status"] == "ok"
    assert status["consecutive_failures"] == 0
    assert status["last_error"] is None
