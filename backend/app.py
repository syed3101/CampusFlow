import os
from collections import Counter
from datetime import date, datetime, time, timedelta
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory, session
from flask_cors import CORS
from mail_services import (
    send_approval_email,
    send_approval_email_to_admin,
    send_approval_email_to_user,
    send_booking_cancellation,
    send_booking_confirmation,
    send_rejection_email,
)
from models import AuditLog, Notification, Reservation, Resource, User, db, utc_now
from sqlalchemy import or_

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"

ACTIVE_BOOKING_STATUSES = {"pending", "confirmed"}


def create_app():
    app = Flask(__name__, static_folder=None)

    app.config["SECRET_KEY"] = os.getenv(
        "SECRET_KEY",
    )
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'instance' / 'campusflow.db'}",
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["COLLEGE_OPEN_TIME"] = time.fromisoformat(
        os.getenv("COLLEGE_OPEN_TIME", "09:30")
    )
    app.config["COLLEGE_CLOSE_TIME"] = time.fromisoformat(
        os.getenv("COLLEGE_CLOSE_TIME", "17:00")
    )
    app.config["COLLEGE_WORKING_DAYS"] = {
        int(day)
        for day in os.getenv(
            "COLLEGE_WORKING_DAYS",
            "0,1,2,3,4,5"
        ).split(",")
    }
    app.config["DAILY_BOOKING_LIMIT"] = int(
        os.getenv("DAILY_BOOKING_LIMIT", "3")
    )
    app.config["CHECKIN_EARLY_MINUTES"] = int(
        os.getenv("CHECKIN_EARLY_MINUTES", "15")
    )
    app.config["NO_SHOW_GRACE_MINUTES"] = int(
        os.getenv("NO_SHOW_GRACE_MINUTES", "15")
    )

    app.config["SESSION_COOKIE_SECURE"] = (
        os.getenv(
            "COOKIE_SECURE",
            "false"
        ).lower()
        == "true"
    )
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    origin = os.getenv("FRONTEND_ORIGIN")
    if origin:
        CORS(
            app,
            origins=[origin],
            supports_credentials=True,
        )

    (BASE_DIR / "instance").mkdir(exist_ok=True)
    db.init_app(app)

    with app.app_context():
        db.create_all()

    def current_user():
        user_id = session.get("user_id")
        return db.session.get(User, user_id) if user_id else None

    def login_required(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                return jsonify(
                    {"error": "Authentication required."}
                ), 401
            return fn(user, *args, **kwargs)

        return wrapper

    def admin_required(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                return jsonify(
                    {"error": "Authentication required."}
                ), 401
            if user.role != "admin":
                return jsonify(
                    {"error": "Admin access required."}
                ), 403
            return fn(user, *args, **kwargs)

        return wrapper

    def parse_date(value):
        try:
            return datetime.strptime(value,"%Y-%m-%d",).date()  # noqa: DTZ007
        except (TypeError, ValueError):
            return None

    def parse_time(value):
        try:
            return datetime.strptime(  # noqa: DTZ007
                value,
                "%H:%M",
            ).time()
        except (TypeError, ValueError):
            return None

    def duration_minutes(start_time, end_time):
        anchor = date(2000, 1, 1)
        start_dt = datetime.combine(anchor, start_time)
        end_dt = datetime.combine(anchor, end_time)
        return int(
            (end_dt - start_dt).total_seconds() // 60
        )

    def active_reservation_query():
        return Reservation.query.filter(
            Reservation.status.in_(ACTIVE_BOOKING_STATUSES)
        )

    def find_overlap(
        resource_id,
        booking_date,
        start_time,
        end_time,
        exclude_reservation_id=None,
    ):
        query = active_reservation_query().filter(
            Reservation.resource_id == resource_id,
            Reservation.date == booking_date,
            Reservation.start_time < end_time,
            Reservation.end_time > start_time,
        )

        if exclude_reservation_id is not None:
            query = query.filter(
                Reservation.id != exclude_reservation_id
            )

        return query.first()

    def has_overlap(
        resource_id,
        booking_date,
        start_time,
        end_time,
        exclude_reservation_id=None,
    ):
        return (
            find_overlap(
                resource_id,
                booking_date,
                start_time,
                end_time,
                exclude_reservation_id,
            )
            is not None
        )

    def computed_resource_status(resource):
        if resource.admin_status != "available":
            return resource.admin_status

        now = datetime.now()  # noqa: DTZ005

        active = Reservation.query.filter(
            Reservation.resource_id == resource.id,
            Reservation.date == now.date(),
            Reservation.status == "confirmed",
            Reservation.start_time <= now.time(),
            Reservation.end_time > now.time(),
        ).first()

        return "booked" if active else "available"

    def create_notification(user_id, message, kind="info"):
        db.session.add(
            Notification(
                user_id=user_id,
                message=message,
                kind=kind,
            )
        )

    def audit(actor_id, action, details=""):
        db.session.add(
            AuditLog(
                actor_user_id=actor_id,
                action=action,
                details=details,
            )
        )

    def suggest_slots(
        resource,
        booking_date,
        start_time,
        end_time,
        limit=3,
    ):
        requested_duration = duration_minutes(
            start_time,
            end_time,
        )

        if requested_duration <= 0:
            return []

        opening = datetime.combine(
            booking_date,
            app.config["COLLEGE_OPEN_TIME"]
        )
        closing = datetime.combine(
            booking_date,
            app.config["COLLEGE_CLOSE_TIME"]
        )
        candidate = opening

        if booking_date == date.today():  # noqa: DTZ011
            now = datetime.now()  # noqa: DTZ005
            rounded_minute = 30 if now.minute < 30 else 60
            if rounded_minute == 60:
                first_future = now.replace(
                    minute=0,
                    second=0,
                    microsecond=0,
                ) + timedelta(hours=1)
            else:
                first_future = now.replace(
                    minute=30,
                    second=0,
                    microsecond=0,
                )

            candidate = max(candidate, first_future)

        suggestions = []

        while (
            candidate
            + timedelta(minutes=requested_duration)
            <= closing
        ):
            candidate_end = candidate + timedelta(
                minutes=requested_duration
            )

            if not has_overlap(
                resource.id,
                booking_date,
                candidate.time(),
                candidate_end.time(),
            ):
                suggestions.append(
                    {
                        "start_time": candidate.strftime("%H:%M"),
                        "end_time": candidate_end.strftime("%H:%M"),
                    }
                )

                if len(suggestions) >= limit:
                    break

            candidate += timedelta(minutes=30)

        return suggestions

    # ---------------------------- AUTH ----------------------------

    @app.post("/api/auth/register")
    def register():
        data = request.get_json(silent=True) or {}

        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""
        role = data.get("role", "student")
        phone_number = (data.get("phone_number") or "").strip()

        if not name or not email or len(password) < 6:
            return jsonify(
                {
                    "error": (
                        "Name, email and a password of at least "
                        "6 characters are required."
                    )
                }
            ), 400

        if role not in {"student", "admin"}:
            return jsonify({"error": "Invalid role."}), 400

        if role == "admin":
            expected = os.getenv(
                "ADMIN_INVITE_CODE",
            )
            if data.get("invite_code") != expected:
                return jsonify(
                    {"error": "Invalid admin invite code."}
                ), 403

        if User.query.filter_by(email=email).first():
            return jsonify(
                {
                    "error": (
                        "An account with this email "
                        "already exists."
                    )
                }
            ), 409

        user = User(
            name=name,
            email=email,
            role=role,
            phone_number=phone_number,
            email_reminders=bool(
                data.get("email_reminders", True)
            ),
            sms_reminders=bool(
                data.get("sms_reminders", False)
            ),
        )
        user.set_password(password)

        db.session.add(user)
        db.session.flush()

        create_notification(
            user.id,
            f"Welcome to CampusFlow, {user.name}.",
            "success",
        )
        audit(
            user.id,
            "account_created",
            f"role={role}",
        )
        db.session.commit()

        session["user_id"] = user.id

        return jsonify({"user": user.to_dict()}), 201

    @app.post("/api/auth/login")
    def login():
        data = request.get_json(silent=True) or {}

        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            return jsonify(
                {"error": "Invalid email or password."}
            ), 401

        session["user_id"] = user.id

        return jsonify({"user": user.to_dict()})

    @app.post("/api/auth/logout")
    def logout():
        session.clear()
        return jsonify({"ok": True})

    @app.get("/api/auth/me")
    def me():
        user = current_user()
        return jsonify(
            {
                "user": (
                    user.to_dict()
                    if user
                    else None
                )
            }
        )

    # -------------------------- RESOURCES --------------------------

    @app.get("/api/resources")
    @login_required
    def list_resources(user):
        query = Resource.query

        q = (request.args.get("q") or "").strip()
        resource_type = request.args.get("type")
        lab = request.args.get("lab")
        category = request.args.get("category")
        requested_status = request.args.get("status")

        if q:
            like = f"%{q}%"
            query = query.filter(
                or_(
                    Resource.name.ilike(like),
                    Resource.type.ilike(like),
                    Resource.category.ilike(like),
                    Resource.lab.ilike(like),
                )
            )

        if resource_type:
            query = query.filter(
                Resource.type == resource_type
            )
        if lab:
            query = query.filter(Resource.lab == lab)
        if category:
            query = query.filter(
                Resource.category == category
            )

        slot_date = parse_date(
            request.args.get("date")
        )
        slot_start = parse_time(
            request.args.get("start_time")
        )
        slot_end = parse_time(
            request.args.get("end_time")
        )
        slot_only = (
            request.args.get("slot_only") == "true"
        )

        resources = []

        for resource in query.order_by(
            Resource.name.asc()
        ).all():
            status = computed_resource_status(resource)

            if (
                requested_status
                and status != requested_status
            ):
                continue

            slot_available = None

            if (
                slot_date
                and slot_start
                and slot_end
                and slot_start < slot_end
            ):
                slot_available = (
                    resource.admin_status == "available"
                    and not has_overlap(
                        resource.id,
                        slot_date,
                        slot_start,
                        slot_end,
                    )
                )

                if slot_only and not slot_available:
                    continue

            resources.append(
                resource.to_dict(
                    computed_status=status,
                    slot_available=slot_available,
                )
            )

        return jsonify({"resources": resources})

    @app.get("/api/resources/filters")
    @login_required
    def resource_filters(user):
        resources = Resource.query.all()

        return jsonify(
            {
                "types": sorted(
                    {r.type for r in resources}
                ),
                "labs": sorted(
                    {r.lab for r in resources}
                ),
                "categories": sorted(
                    {r.category for r in resources}
                ),
            }
        )

    @app.get(
        "/api/resources/<int:resource_id>/availability"
    )
    @login_required
    def availability(user, resource_id):
        resource = db.session.get(
            Resource,
            resource_id,
        )

        if not resource:
            return jsonify(
                {"error": "Resource not found."}
            ), 404

        booking_date = parse_date(
            request.args.get("date")
        )

        if not booking_date:
            return jsonify(
                {"error": "A valid date is required."}
            ), 400

        bookings = (
            active_reservation_query()
            .filter(
                Reservation.resource_id
                == resource_id,
                Reservation.date
                == booking_date,
            )
            .order_by(
                Reservation.start_time.asc()
            )
            .all()
        )

        return jsonify(
            {
                "bookings": [
                    {
                        "start_time": (
                            reservation
                            .start_time
                            .strftime("%H:%M")
                        ),
                        "end_time": (
                            reservation
                            .end_time
                            .strftime("%H:%M")
                        ),
                        "status": reservation.status,
                    }
                    for reservation in bookings
                ],
                "admin_status": (
                    resource.admin_status
                ),
            }
        )

    @app.post("/api/resources")
    @admin_required
    def create_resource(user):
        data = request.get_json(silent=True) or {}
        required = [
            "name",
            "type",
            "category",
            "lab",
        ]

        if any(
            not str(data.get(field, "")).strip()
            for field in required
        ):
            return jsonify(
                {
                    "error": (
                        "Name, type, category and "
                        "lab are required."
                    )
                }
            ), 400

        resource = Resource(
            name=data["name"].strip(),
            type=data["type"].strip(),
            category=data["category"].strip(),
            lab=data["lab"].strip(),
            description=(
                data.get("description") or ""
            ).strip(),
            max_booking_minutes=int(
                data.get(
                    "max_booking_minutes",
                    180,
                )
            ),
            admin_status="available",
            requires_approval=bool(
                data.get(
                    "requires_approval",
                    False,
                )
            ),
        )

        db.session.add(resource)
        db.session.flush()

        audit(
            user.id,
            "resource_created",
            f"resource_id={resource.id}",
        )
        db.session.commit()

        return jsonify(
            {"resource": resource.to_dict()}
        ), 201

    @app.put("/api/resources/<int:resource_id>")
    @admin_required
    def update_resource(user, resource_id):
        resource = db.session.get(
            Resource,
            resource_id,
        )

        if not resource:
            return jsonify(
                {"error": "Resource not found."}
            ), 404

        data = request.get_json(silent=True) or {}
        previous_status = resource.admin_status

        for field in [
            "name",
            "type",
            "category",
            "lab",
            "description",
        ]:
            if field in data:
                setattr(
                    resource,
                    field,
                    str(data[field]).strip(),
                )

        if "max_booking_minutes" in data:
            resource.max_booking_minutes = int(
                data["max_booking_minutes"]
            )

        if "requires_approval" in data:
            resource.requires_approval = bool(
                data["requires_approval"]
            )

        if (
            "status" in data
            or "admin_status" in data
        ):
            new_status = data.get(
                "status",
                data.get("admin_status"),
            )

            if new_status not in {
                "available",
                "maintenance",
                "unavailable",
            }:
                return jsonify(
                    {"error": "Invalid resource status."}
                ), 400

            resource.admin_status = new_status

        if (
            previous_status
            != resource.admin_status
            and resource.admin_status
            == "maintenance"
        ):
            upcoming = Reservation.query.filter(
                Reservation.resource_id
                == resource.id,
                Reservation.status.in_(
                    ACTIVE_BOOKING_STATUSES
                ),
                Reservation.date >= date.today(),  # noqa: DTZ011
            ).all()

            for reservation in upcoming:
                create_notification(
                    reservation.user_id,
                    (
                        f"{resource.name} is under "
                        f"maintenance. Please check "
                        f"your booking on "
                        f"{reservation.date.isoformat()}."
                    ),
                    "warning",
                )

        audit(
            user.id,
            "resource_updated",
            f"resource_id={resource.id}",
        )
        db.session.commit()

        return jsonify(
            {
                "resource": resource.to_dict(
                    computed_status=(
                        computed_resource_status(
                            resource
                        )
                    )
                )
            }
        )

    @app.delete("/api/resources/<int:resource_id>")
    @admin_required
    def delete_resource(user, resource_id):
        resource = db.session.get(
            Resource,
            resource_id,
        )

        if not resource:
            return jsonify(
                {"error": "Resource not found."}
            ), 404

        name = resource.name

        audit(
            user.id,
            "resource_deleted",
            (
                f"resource_id={resource.id}; "
                f"name={name}"
            ),
        )

        db.session.delete(resource)
        db.session.commit()

        return jsonify({"ok": True})

    # ------------------------- RESERVATIONS -------------------------

    @app.post("/api/reservations")
    @login_required
    def create_reservation(user):
        if user.role != "student":
            return jsonify(
                {
                    "error": (
                        "Student account required "
                        "to create a booking."
                    )
                }
            ), 403

        data = request.get_json(silent=True) or {}

        working_days = app.config["COLLEGE_WORKING_DAYS"]

        resource = db.session.get(
            Resource,
            data.get("resource_id"),
        )

        if not resource:
            return jsonify(
                {"error": "Resource not found."}
            ), 404

        if resource.admin_status != "available":
            return jsonify(
                {
                    "error": (
                        f"{resource.name} is currently "
                        f"{resource.admin_status}."
                    )
                }
            ), 409

        booking_date = parse_date(data.get("date"))
        start_time = parse_time(
            data.get("start_time")
        )
        end_time = parse_time(data.get("end_time"))

        if (
            not booking_date
            or not start_time
            or not end_time
        ):
            return jsonify(
                {
                    "error": (
                        "Valid date, start time and "
                        "end time are required."
                    )
                }
            ), 400

        if booking_date.weekday() not in working_days:
            return jsonify({
                "error": "Bookings are not available on this day."
            }), 400

        if booking_date < date.today():  # noqa: DTZ011
            return jsonify(
                {
                    "error": (
                        "Bookings cannot be made "
                        "in the past."
                    )
                }
            ), 400

        if (
            booking_date == date.today()  # noqa: DTZ011
            and start_time <= datetime.now().time()  # noqa: DTZ005
        ):
            return jsonify(
                {
                    "error": (
                        "The booking start time must "
                        "be in the future."
                    )
                }
            ), 400

        if start_time >= end_time:
            return jsonify(
                {
                    "error": (
                        "End time must be later than "
                        "start time."
                    )
                }
            ), 400

        college_open = app.config["COLLEGE_OPEN_TIME"]
        college_close = app.config["COLLEGE_CLOSE_TIME"]

        if (
            start_time < college_open
            or end_time > college_close
        ):
            return jsonify({
                "error": (
                    "Bookings are only allowed between "
                    f"{college_open.strftime('%H:%M')} and "
                    f"{college_close.strftime('%H:%M')}."
                )
            }), 400

        minutes = duration_minutes(
            start_time,
            end_time,
        )

        if minutes > resource.max_booking_minutes:
            return jsonify(
                {
                    "error": (
                        "Maximum booking duration for "
                        f"this resource is "
                        f"{resource.max_booking_minutes} "
                        "minutes."
                    )
                }
            ), 400

        daily_count = Reservation.query.filter(
            Reservation.user_id == user.id,
            Reservation.date == booking_date,
            Reservation.status.in_(
                ACTIVE_BOOKING_STATUSES
            ),
        ).count()

        if (
            daily_count
            >= app.config["DAILY_BOOKING_LIMIT"]
        ):
            return jsonify(
                {
                    "error": (
                        "Daily booking limit reached "
                        f"({app.config['DAILY_BOOKING_LIMIT']} "
                        "bookings)."
                    )
                }
            ), 429

        if has_overlap(
            resource.id,
            booking_date,
            start_time,
            end_time,
        ):
            return jsonify(
                {
                    "error": (
                        "That time overlaps with an "
                        "existing or pending reservation."
                    ),
                    "suggestions": suggest_slots(
                        resource,
                        booking_date,
                        start_time,
                        end_time,
                    ),
                }
            ), 409

        status = (
            "pending"
            if resource.requires_approval
            else "confirmed"
        )

        reservation = Reservation(
            user_id=user.id,
            resource_id=resource.id,
            date=booking_date,
            start_time=start_time,
            end_time=end_time,
            status=status,
        )

        db.session.add(reservation)
        db.session.flush()

        if status == "pending":
            create_notification(
                user.id,
                (
                    f"Booking request submitted: "
                    f"{resource.name} on "
                    f"{booking_date.isoformat()} "
                    f"{start_time.strftime('%H:%M')}–"
                    f"{end_time.strftime('%H:%M')}. "
                    "Waiting for admin approval."
                ),
                "info",
            )

            for admin in User.query.filter_by(role="admin").all():
                create_notification(
                    admin.id,
                    (
                        f"Approval needed: {user.name} requested "
                        f"{resource.name} on "
                        f"{booking_date.isoformat()} "
                        f"{start_time.strftime('%H:%M')}–"
                        f"{end_time.strftime('%H:%M')}."
                    ),
                    "info",
                )

        else:
            create_notification(
                user.id,
                (
                    f"Booking confirmed: "
                    f"{resource.name} on "
                    f"{booking_date.isoformat()} "
                    f"{start_time.strftime('%H:%M')}–"
                    f"{end_time.strftime('%H:%M')}."
                ),
                "success",
            )

        audit(
            user.id,
            "reservation_created",
            (
                f"reservation_id={reservation.id}; "
                f"status={status}"
            ),
        )

        db.session.commit()

        if status == "pending":
            try:
                send_approval_email_to_user(
                    to_email=user.email,
                    student_name=user.name,
                    resource_name=resource.name,
                    booking_date=booking_date.isoformat(),
                    start_time=start_time.strftime("%H:%M"),
                    end_time=end_time.strftime("%H:%M"),
                    lab=resource.lab
                )
                                        
            except Exception as error:  # noqa: BLE001
                app.logger.error(
                    f"Booking email failed: {error}"
                )
                
            for admin in User.query.filter_by(role="admin").all():
                try:
                    send_approval_email_to_admin(
                        to_email=admin.email,
                        student_name=user.name,
                        student_email=user.email,
                        resource_name=resource.name,
                        booking_date=booking_date.isoformat(),
                        start_time=start_time.strftime("%H:%M"),
                        end_time=end_time.strftime("%H:%M"),
                        lab=resource.lab
                    )
                                            
                except Exception as error:  # noqa: BLE001
                    app.logger.error(
                        f"Booking email failed: {error}"
                    )
        
        else:
            try:
                send_booking_confirmation(
                    to_email=user.email,
                    student_name=user.name,
                    resource_name=resource.name,
                    booking_date=booking_date.isoformat(),
                    start_time=start_time.strftime("%H:%M"),
                    end_time=end_time.strftime("%H:%M"),
                    lab=resource.lab,
                )
        
            except Exception as error:  # noqa: BLE001
                app.logger.error(
                    f"Booking email failed: {error}"
                )

        return jsonify({
            "reservation": reservation.to_dict()
        }), 201

    @app.get("/api/reservations")
    @login_required
    def list_reservations(user):
        query = Reservation.query

        if user.role != "admin":
            query = query.filter(
                Reservation.user_id == user.id
            )

        status_filter = request.args.get("status")

        if status_filter:
            query = query.filter(
                Reservation.status
                == status_filter
            )

        reservations = query.order_by(
            Reservation.date.desc(),
            Reservation.start_time.desc(),
        ).all()

        return jsonify(
            {
                "reservations": [
                    reservation.to_dict()
                    for reservation in reservations
                ]
            }
        )

    @app.get("/api/approvals")
    @admin_required
    def approval_queue(user):
        pending = (
            Reservation.query
            .filter(
                Reservation.status == "pending"
            )
            .order_by(
                Reservation.date.asc(),
                Reservation.start_time.asc(),
            )
            .all()
        )

        return jsonify(
            {
                "reservations": [
                    reservation.to_dict()
                    for reservation in pending
                ]
            }
        )

    @app.post(
        "/api/reservations/<int:reservation_id>/approve"
    )
    @admin_required
    def approve_reservation(user, reservation_id):
        reservation = db.session.get(
            Reservation,
            reservation_id,
        )

        if not reservation:
            return jsonify(
                {"error": "Reservation not found."}
            ), 404

        if reservation.status != "pending":
            return jsonify(
                {
                    "error": (
                        "Only pending reservations "
                        "can be approved."
                    )
                }
            ), 409

        if reservation.resource.admin_status != "available":
            return jsonify(
                {
                    "error": (
                        "Resource is no longer "
                        "available."
                    )
                }
            ), 409

        conflict = find_overlap(
            reservation.resource_id,
            reservation.date,
            reservation.start_time,
            reservation.end_time,
            exclude_reservation_id=reservation.id,
        )

        if conflict:
            return jsonify(
                {
                    "error": (
                        "This request now conflicts "
                        "with another active booking."
                    )
                }
            ), 409

        reservation.status = "confirmed"
        reservation.approved_by_id = user.id
        reservation.approved_at = utc_now()

        create_notification(
            reservation.user_id,
            (
                f"Approved: {reservation.resource.name} "
                f"on {reservation.date.isoformat()} "
                f"{reservation.start_time.strftime('%H:%M')}–"
                f"{reservation.end_time.strftime('%H:%M')}."
            ),
            "success",
        )

        audit(
            user.id,
            "reservation_approved",
            f"reservation_id={reservation.id}",
        )

        db.session.commit()

        try:
            send_approval_email(
                to_email=reservation.user.email,
                student_name=reservation.user.name,
                resource_name=reservation.resource.name,
                booking_date=reservation.date.isoformat(),
                start_time=reservation.start_time.strftime("%H:%M"),
                end_time=reservation.end_time.strftime("%H:%M")
            )
    
        except Exception as error:  # noqa: BLE001
            app.logger.error(
                f"Approval email failed: {error}"
            )

        return jsonify(
            {"reservation": reservation.to_dict()}
        )

    @app.post(
        "/api/reservations/<int:reservation_id>/reject"
    )
    @admin_required
    def reject_reservation(user, reservation_id):
        reservation = db.session.get(
            Reservation,
            reservation_id,
        )

        if not reservation:
            return jsonify(
                {"error": "Reservation not found."}
            ), 404

        if reservation.status != "pending":
            return jsonify(
                {
                    "error": (
                        "Only pending reservations "
                        "can be rejected."
                    )
                }
            ), 409

        reservation.status = "rejected"
        reservation.rejected_at = utc_now()

        create_notification(
            reservation.user_id,
            (
                f"Booking request rejected: "
                f"{reservation.resource.name} on "
                f"{reservation.date.isoformat()}."
            ),
            "warning",
        )

        audit(
            user.id,
            "reservation_rejected",
            f"reservation_id={reservation.id}",
        )

        db.session.commit()

        try:
            send_rejection_email(
                to_email=reservation.user.email,
                student_name=reservation.user.name,
                resource_name=reservation.resource.name,
                booking_date=reservation.date.isoformat(),
                start_time=reservation.start_time.strftime("%H:%M"),
                end_time=reservation.end_time.strftime("%H:%M")
            )
            
        except Exception as error:  # noqa: BLE001
            app.logger.error(
                f"Rejection email failed: {error}"
            )

        return jsonify({
            "reservation": reservation.to_dict()
        }), 200


    @app.post(
        "/api/reservations/<int:reservation_id>/check-in"
    )
    @login_required
    def check_in(user, reservation_id):
        reservation = db.session.get(
            Reservation,
            reservation_id,
        )

        if not reservation:
            return jsonify(
                {"error": "Reservation not found."}
            ), 404

        if (
            user.role != "admin"
            and reservation.user_id != user.id
        ):
            return jsonify(
                {
                    "error": (
                        "You cannot check in to "
                        "this reservation."
                    )
                }
            ), 403

        if reservation.status != "confirmed":
            return jsonify(
                {
                    "error": (
                        "Only confirmed reservations "
                        "can be checked in."
                    )
                }
            ), 409

        if reservation.checked_in_at:
            return jsonify(
                {"reservation": reservation.to_dict()}
            )

        now = datetime.now()  # noqa: DTZ005
        start_at = datetime.combine(
            reservation.date,
            reservation.start_time,
        )

        opens_at = start_at - timedelta(
            minutes=app.config[
                "CHECKIN_EARLY_MINUTES"
            ]
        )
        closes_at = start_at + timedelta(
            minutes=app.config[
                "NO_SHOW_GRACE_MINUTES"
            ]
        )

        if now < opens_at:
            return jsonify(
                {
                    "error": (
                        "Check-in opens "
                        f"{app.config['CHECKIN_EARLY_MINUTES']} "
                        "minutes before the booking."
                    )
                }
            ), 409

        if now > closes_at:
            return jsonify(
                {
                    "error": (
                        "The check-in window has closed. "
                        "The booking may be released as "
                        "a no-show."
                    )
                }
            ), 409

        reservation.checked_in_at = now

        create_notification(
            reservation.user_id,
            (
                f"Checked in: "
                f"{reservation.resource.name}."
            ),
            "success",
        )

        audit(
            user.id,
            "reservation_checked_in",
            f"reservation_id={reservation.id}",
        )

        db.session.commit()

        return jsonify(
            {"reservation": reservation.to_dict()}
        )

    @app.delete(
        "/api/reservations/<int:reservation_id>"
    )
    @login_required
    def cancel_reservation(user, reservation_id):
        reservation = db.session.get(
            Reservation,
            reservation_id,
        )

        if not reservation:
            return jsonify(
                {"error": "Reservation not found."}
            ), 404

        if (
            user.role != "admin"
            and reservation.user_id != user.id
        ):
            return jsonify(
                {
                    "error": (
                        "You cannot cancel "
                        "this reservation."
                    )
                }
            ), 403

        if reservation.status not in {
            "pending",
            "confirmed",
        }:
            return jsonify(
                {
                    "error": (
                        "Only pending or confirmed "
                        "reservations can be cancelled."
                    )
                }
            ), 409

        reservation.status = "cancelled"
        reservation.cancelled_at = utc_now()

        create_notification(
            reservation.user_id,
            (
                f"Booking cancelled: "
                f"{reservation.resource.name} on "
                f"{reservation.date.isoformat()}."
            ),
            "warning",
        )

        audit(
            user.id,
            "reservation_cancelled",
            f"reservation_id={reservation.id}",
        )

        db.session.commit()

        try:
            send_booking_cancellation(
                to_email=reservation.user.email,
                student_name=reservation.user.name,
                resource_name=reservation.resource.name,
                booking_date=reservation.date.isoformat(),
                start_time=reservation.start_time.strftime("%H:%M"),
                end_time=reservation.end_time.strftime("%H:%M")
            )

        except Exception as error:  # noqa: BLE001
            app.logger.error(
                f"Cancellation email failed: {error}"
            )
        return jsonify({
            "reservation": reservation.to_dict()
        }), 200

    # ------------------------ NOTIFICATIONS ------------------------

    @app.get("/api/notifications")
    @login_required
    def notifications(user):
        rows = (
            Notification.query
            .filter_by(user_id=user.id)
            .order_by(
                Notification.created_at.desc()
            )
            .limit(50)
            .all()
        )

        return jsonify(
            {
                "notifications": [
                    notification.to_dict()
                    for notification in rows
                ]
            }
        )

    @app.post(
        "/api/notifications/<int:notification_id>/read"
    )
    @login_required
    def mark_notification_read(
        user,
        notification_id,
    ):
        notification = db.session.get(
            Notification,
            notification_id,
        )

        if (
            not notification
            or notification.user_id != user.id
        ):
            return jsonify(
                {"error": "Notification not found."}
            ), 404

        notification.is_read = True
        db.session.commit()

        return jsonify(
            {
                "notification": (
                    notification.to_dict()
                )
            }
        )

    # -------------------------- DASHBOARD --------------------------

    @app.get("/api/dashboard")
    @admin_required
    def dashboard(user):
        resources = Resource.query.order_by(
            Resource.name.asc()
        ).all()

        reservations = Reservation.query.all()

        confirmed = [
            reservation
            for reservation in reservations
            if reservation.status == "confirmed"
        ]

        statuses = Counter(
            computed_resource_status(resource)
            for resource in resources
        )

        today_bookings = sum(
            1
            for reservation in confirmed
            if reservation.date == date.today()  # noqa: DTZ011
        )

        use_count = Counter(
            reservation.resource_id
            for reservation in confirmed
        )

        ranked = [
            {
                "resource_id": resource.id,
                "name": resource.name,
                "bookings": use_count.get(
                    resource.id,
                    0,
                ),
            }
            for resource in resources
        ]

        most_used = sorted(
            ranked,
            key=lambda row: (
                -row["bookings"],
                row["name"],
            ),
        )[:5]

        least_used = sorted(
            ranked,
            key=lambda row: (
                row["bookings"],
                row["name"],
            ),
        )[:5]

        peak_count = Counter(
            reservation.start_time.hour
            for reservation in confirmed
        )

        peak_hours = [
            {
                "hour": hour,
                "bookings": count,
            }
            for hour, count
            in sorted(peak_count.items())
        ]

        total_minutes = sum(
            max(
                0,
                duration_minutes(
                    reservation.start_time,
                    reservation.end_time,
                ),
            )
            for reservation in confirmed
        )

        if confirmed:
            first_day = min(
                reservation.date
                for reservation in confirmed
            )
            observed_days = max(
                1,
                (date.today() - first_day).days + 1,  # noqa: DTZ011
            )
        else:
            observed_days = 1

        capacity_minutes = max(
            1,
            len(resources)
            * observed_days
            * 12
            * 60,
        )

        utilization_rate = round(
            min(
                100,
                (
                    total_minutes
                    / capacity_minutes
                )
                * 100,
            ),
            1,
        )

        return jsonify(
            {
                "totals": {
                    "total_resources": len(resources),
                    "available": statuses["available"],
                    "booked": statuses["booked"],
                    "maintenance": statuses["maintenance"],
                    "unavailable": statuses["unavailable"],
                    "todays_bookings": today_bookings,
                    "pending_approvals": sum(
                        1
                        for reservation
                        in reservations
                        if reservation.status
                        == "pending"
                    ),
                    "no_shows": sum(
                        1
                        for reservation
                        in reservations
                        if reservation.status
                        == "no_show"
                    ),
                },
                "most_used_resources": most_used,
                "least_used_resources": least_used,
                "peak_hours": peak_hours,
                "total_cancellations": sum(
                    1
                    for reservation
                    in reservations
                    if reservation.status
                    == "cancelled"
                ),
                "utilization_rate": (
                    utilization_rate
                ),
            }
        )

# ------------------------ HEALTH ------------------------
    @app.get("/api/health")
    def health():
        return jsonify({
            "status": "ok",
            "service": "CampusFlow"
        }), 200

    # ----------------------- FRONTEND BUILD ------------------------

    @app.get("/")
    @app.get("/<path:path>")
    def serve_react(path=""):
        if not FRONTEND_DIST.exists():
            return jsonify(
                {
                    "message": (
                        "CampusFlow API is running. "
                        "Start the Vite frontend on "
                        "http://localhost:5173, or "
                        "run npm run build inside "
                        "frontend."
                    )
                }
            )

        requested = FRONTEND_DIST / path

        if path and requested.is_file():
            return send_from_directory(
                FRONTEND_DIST,
                path,
            )

        return send_from_directory(
            FRONTEND_DIST,
            "index.html",
        )

    return app


app = create_app()

if __name__ == "__main__":
    app.run(
        debug=True,
        port=5000,
    )
