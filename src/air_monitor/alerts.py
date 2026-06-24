from __future__ import annotations

import logging
import shlex
import socket
import subprocess
from dataclasses import dataclass, field
from typing import Protocol

LOGGER = logging.getLogger(__name__)


class AlertNotifier(Protocol):
    def send_failure_alert(self, status: dict[str, object]) -> None: ...


@dataclass(frozen=True)
class NullAlertNotifier:
    def send_failure_alert(self, status: dict[str, object]) -> None:
        return None


@dataclass(frozen=True)
class MailAlertNotifier:
    recipient: str
    command: tuple[str, ...] = ("mail",)
    subject_prefix: str = "[AIR MONITOR]"
    hostname: str = field(default_factory=socket.gethostname)

    def send_failure_alert(self, status: dict[str, object]) -> None:
        subject = f"{self.subject_prefix} collection failed on {self.hostname}"
        body = _format_alert_body(status=status, hostname=self.hostname)
        command = [*self.command, "-s", subject, self.recipient]
        LOGGER.info("Sending air monitor alert to %s", self.recipient)
        subprocess.run(command, input=body, text=True, timeout=20, check=True)


def build_alert_notifier(
    *,
    recipient: str | None,
    command: str,
    subject_prefix: str,
) -> AlertNotifier:
    if not recipient:
        return NullAlertNotifier()

    command_parts = tuple(shlex.split(command)) or ("mail",)
    return MailAlertNotifier(
        recipient=recipient,
        command=command_parts,
        subject_prefix=subject_prefix,
    )


def _format_alert_body(*, status: dict[str, object], hostname: str) -> str:
    return "\n".join(
        [
            f"Air Monitor could not collect data on {hostname}.",
            "",
            f"Status: {status.get('collection_status')}",
            f"Consecutive failures: {status.get('consecutive_failures')}",
            f"Last run: {status.get('last_run_at')}",
            f"Last success: {status.get('last_success_at')}",
            f"Last error: {status.get('last_error')}",
            "",
            "Most likely causes:",
            "- expired PHP session cookie",
            "- device unavailable on the local network",
            "- response format changed",
        ]
    )
