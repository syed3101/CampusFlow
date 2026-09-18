import os
from datetime import datetime, timedelta

from app import app
from apscheduler.schedulers.blocking import BlockingScheduler
from mail_services import send_email
from models import Notification, Reservation, db


def booking_start(reservation):
    return datetime.combine(
        reservation.date,
        reservation.start_time,
    )


def run_booking_jobs():
    now = datetime.now()  # noqa: DTZ005
    reminder_minutes = int(os.getenv("REMINDER_MINUTES", "30"))
    no_show_grace = int(os.getenv("NO_SHOW_GRACE_MINUTES", "15"))

    with app.app_context():
        changed = False

        # 1) Booking reminders
        confirmed = Reservation.query.filter(
            Reservation.status == "confirmed"
        ).all()

        for reservation in confirmed:
            start_at = booking_start(reservation)
            delta = start_at - now

            if (
                reservation.reminder_sent_at is None
                and timedelta(0) <= delta <= timedelta(minutes=reminder_minutes)
            ):
                message = (
                    f"Reminder: {reservation.resource.name} is booked "
                    f"today at {reservation.start_time.strftime('%H:%M')} "
                    f"in {reservation.resource.lab}."
                )

                db.session.add(
                    Notification(
                        user_id=reservation.user_id,
                        message=message,
                        kind="info",
                    )
                )

                user = reservation.user

                if user.email_reminders:
                    send_email(
                        user.email,
                        "CampusFlow booking reminder",
                        message,
                    )

                reservation.reminder_sent_at = now
                changed = True

        # 2) Automatic no-show release
        for reservation in confirmed:
            if reservation.checked_in_at is not None:
                continue

            release_at = booking_start(reservation) + timedelta(
                minutes=no_show_grace
            )

            if now >= release_at:
                reservation.status = "no_show"
                reservation.no_show_released_at = now

                db.session.add(
                    Notification(
                        user_id=reservation.user_id,
                        message=(
                            f"Your booking for {reservation.resource.name} "
                            f"was released as a no-show after "
                            f"{no_show_grace} minutes."
                        ),
                        kind="warning",
                    )
                )
                changed = True

        if changed:
            db.session.commit()


if __name__ == "__main__":
    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_booking_jobs,
        "interval",
        seconds=60,
        max_instances=1,
        coalesce=True,
    )

    print("CampusFlow background worker started.")
    print(" - reminders: every 60 seconds")
    print(" - no-show release: every 60 seconds")
    run_booking_jobs()
    scheduler.start()
