from datetime import UTC, datetime

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()

def utc_now():
    return datetime.now(UTC).replace(tzinfo=None)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")

    phone_number = db.Column(db.String(40), default="")
    email_reminders = db.Column(db.Boolean, nullable=False, default=True)
    sms_reminders = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    reservations = db.relationship(
        "Reservation",
        foreign_keys="Reservation.user_id",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan",
    )
    notifications = db.relationship(
        "Notification",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "phone_number": self.phone_number or "",
            "email_reminders": self.email_reminders,
            "sms_reminders": self.sms_reminders,
        }


class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    type = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    lab = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default="")
    max_booking_minutes = db.Column(db.Integer, nullable=False, default=180)
    admin_status = db.Column(db.String(30), nullable=False, default="available")

    # Some high-value / sensitive lab resources can require an admin decision.
    requires_approval = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    reservations = db.relationship(
        "Reservation",
        backref="resource",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def to_dict(self, computed_status=None, slot_available=None):
        payload = {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "category": self.category,
            "lab": self.lab,
            "description": self.description or "",
            "max_booking_minutes": self.max_booking_minutes,
            "admin_status": self.admin_status,
            "status": computed_status or self.admin_status,
            "requires_approval": self.requires_approval,
        }
        if slot_available is not None:
            payload["slot_available"] = slot_available
        return payload


class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False,
        index=True,
    )
    resource_id = db.Column(
        db.Integer,
        db.ForeignKey("resource.id"),
        nullable=False,
        index=True,
    )

    date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

    # pending -> confirmed/rejected
    # confirmed -> cancelled/no_show
    status = db.Column(db.String(30), nullable=False, default="confirmed")

    approved_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    approved_at = db.Column(db.DateTime)
    rejected_at = db.Column(db.DateTime)
    cancelled_at = db.Column(db.DateTime)

    checked_in_at = db.Column(db.DateTime)
    no_show_released_at = db.Column(db.DateTime)
    reminder_sent_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    approver = db.relationship("User", foreign_keys=[approved_by_id])

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_name": self.user.name,
            "resource_id": self.resource_id,
            "resource_name": self.resource.name,
            "lab": self.resource.lab,
            "requires_approval": self.resource.requires_approval,
            "date": self.date.isoformat(),
            "start_time": self.start_time.strftime("%H:%M"),
            "end_time": self.end_time.strftime("%H:%M"),
            "status": self.status,
            "checked_in_at": (
                self.checked_in_at.isoformat() if self.checked_in_at else None
            ),
            "approved_at": (
                self.approved_at.isoformat() if self.approved_at else None
            ),
            "approved_by": (
                self.approver.name if self.approver else None
            ),
            "created_at": self.created_at.isoformat(),
            "cancelled_at": (
                self.cancelled_at.isoformat() if self.cancelled_at else None
            ),
            "no_show_released_at": (
                self.no_show_released_at.isoformat()
                if self.no_show_released_at
                else None
            ),
        }


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False,
        index=True,
    )
    message = db.Column(db.String(500), nullable=False)
    kind = db.Column(db.String(30), nullable=False, default="info")
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    def to_dict(self):
        return {
            "id": self.id,
            "message": self.message,
            "kind": self.kind,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat(),
        }


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    action = db.Column(db.String(120), nullable=False)
    details = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
