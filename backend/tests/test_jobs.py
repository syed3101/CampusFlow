from datetime import datetime, timedelta  # noqa: F401

import pytest

pytest.importorskip("apscheduler")

import jobs as jobs_module
from models import Notification, Reservation, db


def _create_confirmed_booking(
    student_client,
    admin_client,
    create_resource,
    booking_date,
    start_time,
    end_time,
):
    resource = create_resource()

    response = student_client.post(
        "/api/reservations",
        json={
            "resource_id": resource["id"],
            "date": booking_date,
            "start_time": start_time,
            "end_time": end_time,
        },
    )
    assert response.status_code == 201
    return response.get_json()["reservation"]


def test_reminder_job_persists_notification_and_marks_reminder_sent(
    app,
    student_client,
    admin_client,
    create_resource,
    future_date,
    monkeypatch,
):
    """
    This test exposes a bug in the uploaded jobs.py.

    Current reminder logic:
      - creates a Notification
      - sends email
      - but never sets reservation.reminder_sent_at
      - and never sets changed = True

    Therefore the reminder transaction may never be committed and can repeat
    every scheduler run.
    """
    reservation = _create_confirmed_booking(
        student_client,
        admin_client,
        create_resource,
        future_date,
        "10:00",
        "11:00",
    )

    fixed_now = datetime.fromisoformat(f"{future_date}T09:40:00")

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now

    monkeypatch.setattr(jobs_module, "app", app)
    monkeypatch.setattr(jobs_module, "datetime", FixedDateTime)

    sent = []
    monkeypatch.setattr(
        jobs_module,
        "send_email",
        lambda *args, **kwargs: sent.append((args, kwargs)),
    )

    jobs_module.run_booking_jobs()

    with app.app_context():
        saved = db.session.get(Reservation, reservation["id"])
        reminders = Notification.query.filter(
            Notification.user_id == saved.user_id,
            Notification.message.like("Reminder:%"),
        ).all()

        assert saved.reminder_sent_at is not None
        assert len(reminders) == 1

    assert len(sent) == 1


def test_no_show_job_releases_missed_booking(
    app,
    student_client,
    admin_client,
    create_resource,
    future_date,
    monkeypatch,
):
    reservation = _create_confirmed_booking(
        student_client,
        admin_client,
        create_resource,
        future_date,
        "10:00",
        "11:00",
    )

    fixed_now = datetime.fromisoformat(f"{future_date}T10:20:00")

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now

    monkeypatch.setattr(jobs_module, "app", app)
    monkeypatch.setattr(jobs_module, "datetime", FixedDateTime)
    monkeypatch.setattr(
        jobs_module,
        "send_email",
        lambda *args, **kwargs: True,
    )

    jobs_module.run_booking_jobs()

    with app.app_context():
        saved = db.session.get(Reservation, reservation["id"])
        assert saved.status == "no_show"
        assert saved.no_show_released_at is not None
