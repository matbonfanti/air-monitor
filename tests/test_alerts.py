from air_monitor.alerts import MailAlertNotifier, NullAlertNotifier, build_alert_notifier


def test_build_alert_notifier_returns_null_notifier_without_recipient():
    notifier = build_alert_notifier(
        recipient=None,
        command="",
        subject_prefix="[AIR MONITOR]",
    )

    assert isinstance(notifier, NullAlertNotifier)


def test_build_alert_notifier_falls_back_to_mail_for_empty_command():
    notifier = build_alert_notifier(
        recipient="matteo@example.test",
        command="",
        subject_prefix="[AIR MONITOR]",
    )

    assert isinstance(notifier, MailAlertNotifier)
    assert notifier.command == ("mail",)
