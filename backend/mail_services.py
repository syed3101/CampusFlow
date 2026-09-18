import os
import smtplib
from email.message import EmailMessage

sender_email = os.getenv("MAIL_USERNAME")
sender_password = os.getenv("MAIL_PASSWORD")

# ------------------------ NOTIFICATIONS ------------------------

def send_booking_confirmation(
    to_email,
    student_name,
    resource_name,
    booking_date,
    start_time,
    end_time,
    lab
):

    if not sender_email or not sender_password:
        print("Email credentials are not configured.")
        return

    message = EmailMessage()

    message["Subject"] = f"CampusFlow Booking Confirmed - {resource_name}"
    message["From"] = sender_email
    message["To"] = to_email

    message.set_content(
        f"""
Hello {student_name},
Your CampusFlow booking has been confirmed.
Resource: {resource_name}
Lab: {lab}
Date: {booking_date}
Time: {start_time} - {end_time}
Please arrive on time and follow the laboratory/resource usage guidelines.
Thank you,
CampusFl"""
    )

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            print("Connected")
            server.login(
                sender_email,
                sender_password
            )
            print("Logged in")
            server.send_message(message)
            print("sent")
    except Exception as exc:  # noqa: BLE001
            print(f"[EMAIL ERROR] {exc}")
            return False

def send_booking_cancellation(
    to_email,
    student_name,
    resource_name,
    booking_date,
    start_time,
    end_time
):
    
    if not sender_email or not sender_password:
        return

    message = EmailMessage()

    message["Subject"] = (
        f"CampusFlow Booking Cancelled - {resource_name}"
    )

    message["From"] = sender_email
    message["To"] = to_email

    message.set_content(
        f"""
Hello {student_name},
Your CampusFlow reservation has been cancelled.
Resource: {resource_name}
Date: {booking_date}
Time: {start_time} - {end_time}
If needed, you can return to CampusFlow and reserve another available slot.
Thank you,
CampusFlow
"""
    )

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            print("Connected")
            server.login(
                sender_email,
                sender_password
            )
            print("Logged in")
            server.send_message(message)
            print("sent")
    except Exception as exc:  # noqa: BLE001
            print(f"[EMAIL ERROR] {exc}")
            return False

def send_approval_email_to_admin(
    to_email,
    student_name,
    student_email,
    resource_name,
    booking_date,
    start_time,
    end_time,
    lab
):
    
    if not sender_email or not sender_password:
        return

    message = EmailMessage()

    message["Subject"] = (
        f"CampusFlow Booking Approval - {resource_name}"
    )

    message["From"] = sender_email
    message["To"] = to_email

    message.set_content(
        f"""
A new CampusFlow booking requires approval.

Student: {student_name}
Email: {student_email}
Resource: {resource_name}
Lab: {lab}
Date: {booking_date}
Time: {start_time} - {end_time}

Kindly visit CampusFlow to approve.
"""
    )

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            print("connected")            
            server.login(
                sender_email,
                sender_password
            )
            print("log")
            server.send_message(message)
            print("sent")
    except Exception as exc:  # noqa: BLE001
            print(f"[EMAIL ERROR] {exc}")
            return False

def send_approval_email_to_user(
    to_email,
    student_name,
    resource_name,
    booking_date,
    start_time,
    end_time,
    lab
):
    
    if not sender_email or not sender_password:
        return

    message = EmailMessage()

    message["Subject"] = (
        f"CampusFlow Booking Request - {resource_name}"
    )

    message["From"] = sender_email
    message["To"] = to_email

    message.set_content(
        f"""
Hello {student_name},
Your CampusFlow request has been submitted.
Resource: {resource_name}
Lab: {lab}
Date: {booking_date}
Time: {start_time} - {end_time}

Waiting for admin approval.

Thank you,
CampusFlow
"""
    )

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            print("connected")
            server.login(
                sender_email,
                sender_password
            )
            print("log")
            server.send_message(message)
            print("sent")
    except Exception as exc:  # noqa: BLE001
            print(f"[EMAIL ERROR] {exc}")
            return False

def send_approval_email(
    to_email,
    student_name,
    resource_name,
    booking_date,
    start_time,
    end_time
):
    
    if not sender_email or not sender_password:
        return

    message = EmailMessage()

    message["Subject"] = (
        f"CampusFlow Booking Approved - {resource_name}"
    )

    message["From"] = sender_email
    message["To"] = to_email

    message.set_content(
        f"""
Hello {student_name},
Your CampusFlow reservation has been approved.
Resource: {resource_name}
Date: {booking_date}
Time: {start_time} - {end_time}
Please arrive on time and follow the laboratory/resource usage guidelines.
Thank you,
CampusFlow
"""
    )

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            print("Connected")
            server.login(
                sender_email,
                sender_password
            )
            print("LOGGED in")
            server.send_message(message)
            print("sent")
    except Exception as exc:  # noqa: BLE001
            print(f"[EMAIL ERROR] {exc}")
            return False

def send_rejection_email(
    to_email,
    student_name,
    resource_name,
    booking_date,
    start_time,
    end_time
):
    
    if not sender_email or not sender_password:
        return

    message = EmailMessage()

    message["Subject"] = (
        f"CampusFlow Booking Rejec - {resource_name}"
    )

    message["From"] = sender_email
    message["To"] = to_email

    message.set_content(
        f"""
Hello {student_name},
Your CampusFlow reservation has been rejected.
Resource: {resource_name}
Date: {booking_date}
Time: {start_time} - {end_time}
If needed, you can return to CampusFlow and reserve another available slot.
Thank you,
CampusFl
"""
    )
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()

            server.login(
                sender_email,
                sender_password
            )

            server.send_message(message)
    except Exception as exc:  # noqa: BLE001
            print(f"[EMAIL ERROR] {exc}")
            return False

# ------------------------ Remainders ------------------------

def send_email(to_email, subject, body):

    if not sender_email or not sender_password:
        return
    
    message = EmailMessage()
    message["From"] = sender_email
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
            server.starttls()
            print("connected")
            server.login(
                sender_email,
                sender_password
            )
            print("log")
            server.send_message(message)
            print("sent")
    except Exception as exc:  # noqa: BLE001
        print(f"[EMAIL ERROR] {exc}")
        return False

