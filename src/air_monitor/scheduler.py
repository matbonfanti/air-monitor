from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime, timedelta

from air_monitor.alerts import AlertNotifier, build_alert_notifier
from air_monitor.collector import collect_readings
from air_monitor.config import Settings
from air_monitor.db import ReadingStore

LOGGER = logging.getLogger(__name__)


def collect_once(settings: Settings, store: ReadingStore) -> int:
    if not settings.device_url:
        msg = "AIR_DEVICE_URL is not configured"
        raise RuntimeError(msg)

    readings = collect_readings(
        url=settings.device_url,
        rooms=settings.rooms,
        cookie=settings.device_cookie,
        timeout_seconds=settings.request_timeout_seconds,
        verify_ssl=settings.verify_ssl,
    )
    return store.add_readings(readings)


class CollectorScheduler:
    def __init__(
        self,
        settings: Settings,
        store: ReadingStore,
        notifier: AlertNotifier | None = None,
    ) -> None:
        self.settings = settings
        self.store = store
        self.notifier = notifier or build_alert_notifier(
            recipient=settings.alert_email_to,
            command=settings.alert_command,
            subject_prefix=settings.alert_subject_prefix,
        )
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._last_run_at: datetime | None = None
        self._last_success_at: datetime | None = None
        self._last_error: str | None = None
        self._consecutive_failures = 0
        self._last_alert_at: datetime | None = None
        self._last_alert_error: str | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        self._thread = threading.Thread(target=self._run, name="air-monitor-collector", daemon=True)
        self._thread.start()

    def stop(self, *, timeout_seconds: float = 5.0) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=timeout_seconds)

    def status(self) -> dict[str, object]:
        with self._lock:
            return self._status_unlocked(now=datetime.now(UTC))

    def _run(self) -> None:
        while not self._stop.is_set():
            self._collect_and_record_status()
            if self._stop.wait(self.settings.poll_seconds):
                break

    def _collect_and_record_status(self) -> None:
        self._set_last_run()
        try:
            count = collect_once(self.settings, self.store)
        except Exception as exc:
            LOGGER.exception("Air monitor collection failed")
            status = self._set_last_error(str(exc))
            self._maybe_send_alert(status)
            return

        LOGGER.info("Collected %s air monitor readings", count)
        self._set_last_success()

    def _set_last_run(self) -> None:
        with self._lock:
            self._last_run_at = datetime.now(UTC)

    def _set_last_success(self) -> None:
        with self._lock:
            self._last_success_at = datetime.now(UTC)
            self._last_error = None
            self._consecutive_failures = 0
            self._last_alert_error = None

    def _set_last_error(self, error: str) -> dict[str, object]:
        with self._lock:
            self._last_error = error
            self._consecutive_failures += 1
            return self._status_unlocked(now=datetime.now(UTC))

    def _maybe_send_alert(self, status: dict[str, object]) -> None:
        if not self.settings.alert_email_to:
            return

        if self._consecutive_failures < self.settings.alert_after_failures:
            return

        if not self._alert_cooldown_elapsed():
            return

        with self._lock:
            self._last_alert_at = datetime.now(UTC)
            status = self._status_unlocked(now=datetime.now(UTC))

        try:
            self.notifier.send_failure_alert(status)
        except Exception as exc:
            LOGGER.exception("Air monitor alert failed")
            with self._lock:
                self._last_alert_error = str(exc)

    def _alert_cooldown_elapsed(self) -> bool:
        if self._last_alert_at is None:
            return True
        cooldown = timedelta(seconds=self.settings.alert_cooldown_seconds)
        return datetime.now(UTC) - self._last_alert_at >= cooldown

    def _collection_status(self, *, now: datetime) -> str:
        if self._last_success_at is None and self._last_error is None:
            return "pending"

        if self._consecutive_failures > 0:
            return "error"

        if self._last_success_at is None:
            return "error"

        stale_after = timedelta(seconds=self.settings.stale_after_seconds)
        if now - self._last_success_at > stale_after:
            return "stale"

        return "ok"

    def _status_unlocked(self, *, now: datetime) -> dict[str, object]:
        return {
            "running": bool(self._thread and self._thread.is_alive()),
            "collection_status": self._collection_status(now=now),
            "last_run_at": _iso_or_none(self._last_run_at),
            "last_success_at": _iso_or_none(self._last_success_at),
            "last_error": self._last_error,
            "consecutive_failures": self._consecutive_failures,
            "stale_after_seconds": self.settings.stale_after_seconds,
            "alert_enabled": bool(self.settings.alert_email_to),
            "last_alert_at": _iso_or_none(self._last_alert_at),
            "last_alert_error": self._last_alert_error,
        }


def _iso_or_none(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat(timespec="seconds")
