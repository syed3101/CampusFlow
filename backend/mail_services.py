import html
import os

from brevo import Brevo
from brevo.transactional_emails import (
    SendTransacEmailRequestSender,
    SendTransacEmailRequestToItem,
)


def _send(to_email, subject, body):
    api_key = os.getenv("BREVO_API_KEY")
    sender_email = os.getenv("BREVO_SENDER_EMAIL")
    sender_name = os.getenv(
        "BREVO_SENDER_NAME",
        "CampusFlow",
    )

    if not api_key:
        print("[EMAIL ERROR] BREVO_API_KEY is missing.")
        return False

    if not sender_email:
        print("[EMAIL ERROR] BREVO_SENDER_EMAIL is missing.")
        return False

    try:
        client = Brevo(
            api_key=api_key,
            timeout=10.0,
        )

        safe_body = html.escape(body).replace(
            "\n",
            "<br>",
        )

        result = (
            client.transactional_emails
            .send_transac_email(
                subject=subject,
                html_content=f"""
                <html>
                    <body style="
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                    ">
                        {safe_body}
                    </body>
                </html>
                """,
                sender=SendTransacEmailRequestSender(
                    name=sender_name,
                    email=sender_email,
                ),
                to=[
                    SendTransacEmailRequestToItem(
                        email=to_email,
                    )
                ],
                request_options={
                    "timeout_in_seconds": 10,
                    "max_retries": 1,
                },
            )
        )

        print(
            "[EMAIL SENT]",
            result.message_id,
        )
        return True

    except Exception as exc:  # noqa: BLE001
        print(f"[EMAIL ERROR] {exc}")
        return False


def send_booking_confirmation(
    to_email,
    student_name,
    resource_name,
    booking_date,
    start_time,
    end_time,
    lab,
):
    return _send(
        to_email,
        f"CampusFlow Booking Confirmed - {resource_name}",
        f"""
Hello {student_name},

Your CampusFlow booking has been confirmed.

Resource: {resource_name}
Lab: {lab}
Date: {booking_date}
Time: {start_time} - {end_time}

Please arrive on time and follow the resource usage guidelines.

Thank you,
CampusFlow
""",
    )


def send_booking_cancellation(
    to_email,
    student_name,
    resource_name,
    booking_date,
    start_time,
    end_time,
):
    return _send(
        to_email,
        f"CampusFlow Booking Cancelled - {resource_name}",
        f"""
Hello {student_name},

Your CampusFlow reservation has been cancelled.

Resource: {resource_name}
Date: {booking_date}
Time: {start_time} - {end_time}

You can return to CampusFlow and reserve another available slot.

Thank you,
CampusFlow
""",
    )


def send_approval_email_to_admin(
    to_email,
    student_name,
    student_email,
    resource_name,
    booking_date,
    start_time,
    end_time,
    lab,
):
    return _send(
        to_email,
        f"CampusFlow Booking Approval - {resource_name}",
        f"""
A new CampusFlow booking requires approval.

Student: {student_name}
Email: {student_email}
Resource: {resource_name}
Lab: {lab}
Date: {booking_date}
Time: {start_time} - {end_time}

Visit CampusFlow to approve or reject the request.
""",
    )


def send_approval_email_to_user(
    to_email,
    student_name,
    resource_name,
    booking_date,
    start_time,
    end_time,
    lab,
):
    return _send(
        to_email,
        f"CampusFlow Booking Request - {resource_name}",
        f"""
Hello {student_name},

Your CampusFlow booking request has been submitted.

Resource: {resource_name}
Lab: {lab}
Date: {booking_date}
Time: {start_time} - {end_time}

Waiting for admin approval.

Thank you,
CampusFlow
""",
    )


def send_approval_email(
    to_email,
    student_name,
    resource_name,
    booking_date,
    start_time,
    end_time,
):
    return _send(
        to_email,
        f"CampusFlow Booking Approved - {resource_name}",
        f"""
Hello {student_name},

Your CampusFlow reservation has been approved.

Resource: {resource_name}
Date: {booking_date}
Time: {start_time} - {end_time}

Please arrive on time.

Thank you,
CampusFlow
""",
    )


def send_rejection_email(
    to_email,
    student_name,
    resource_name,
    booking_date,
    start_time,
    end_time,
):
    return _send(
        to_email,
        f"CampusFlow Booking Rejected - {resource_name}",
        f"""
Hello {student_name},

Your CampusFlow reservation has been rejected.

Resource: {resource_name}
Date: {booking_date}
Time: {start_time} - {end_time}

You can return to CampusFlow and choose another available slot.

Thank you,
CampusFlow
""",
    )


def send_email(
    to_email,
    subject,
    body,
):
    return _send(
        to_email,
        subject,
        body,
    )