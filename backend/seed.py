from datetime import date, time, timedelta

from app import app
from models import Reservation, Resource, User, db


def seed():
    with app.app_context():
        db.create_all()

        admin = User.query.filter_by(
            email="admin@campusflow.edu"
        ).first()

        if not admin:
            admin = User(
                name="CampusFlow Admin",
                email="admin@campusflow.edu",
                role="admin",
                email_reminders=True,
            )
            admin.set_password("admin123")
            db.session.add(admin)

        student = User.query.filter_by(
            email="student@campusflow.edu"
        ).first()

        if not student:
            student = User(
                name="Demo Student",
                email="student@campusflow.edu",
                role="student",
                email_reminders=True,
            )
            student.set_password("student123")
            db.session.add(student)

        db.session.flush()

        if Resource.query.count() == 0:
            resources = [
                Resource(
                    name="Prusa MK4 3D Printer",
                    type="3D Printer",
                    category="Prototyping",
                    lab="Innovation Lab",
                    description=(
                        "High-speed FDM printer for "
                        "student prototypes."
                    ),
                    max_booking_minutes=180,
                    requires_approval=False,
                ),
                Resource(
                    name="NVIDIA RTX Workstation",
                    type="Workstation",
                    category="Computing",
                    lab="AI Lab",
                    description=(
                        "GPU workstation for ML and "
                        "rendering workloads."
                    ),
                    max_booking_minutes=240,
                    requires_approval=True,
                ),
                Resource(
                    name="Digital Oscilloscope",
                    type="Oscilloscope",
                    category="Electronics",
                    lab="EEE Lab",
                    description=(
                        "100 MHz four-channel digital "
                        "oscilloscope."
                    ),
                    max_booking_minutes=120,
                    requires_approval=False,
                ),
                Resource(
                    name="Laser Cutter",
                    type="Laser Cutter",
                    category="Fabrication",
                    lab="Maker Space",
                    description=(
                        "CO2 laser cutter for acrylic "
                        "and thin wood."
                    ),
                    max_booking_minutes=90,
                    requires_approval=True,
                ),
                Resource(
                    name="DSLR Camera Kit",
                    type="Camera",
                    category="Media",
                    lab="Media Lab",
                    description=(
                        "Camera, lens and tripod kit "
                        "for campus projects."
                    ),
                    max_booking_minutes=240,
                    requires_approval=True,
                ),
            ]

            db.session.add_all(resources)
            db.session.flush()

        if Reservation.query.count() == 0:
            printer = Resource.query.filter_by(
                name="Prusa MK4 3D Printer"
            ).first()

            workstation = Resource.query.filter_by(
                name="NVIDIA RTX Workstation"
            ).first()

            db.session.add_all(
                [
                    Reservation(
                        user_id=student.id,
                        resource_id=printer.id,
                        date=(
                            date.today()  # noqa: DTZ011
                            + timedelta(days=1)
                        ),
                        start_time=time(10, 0),
                        end_time=time(11, 0),
                        status="confirmed",
                    ),
                    Reservation(
                        user_id=student.id,
                        resource_id=workstation.id,
                        date=(
                            date.today()  # noqa: DTZ011
                            + timedelta(days=2)
                        ),
                        start_time=time(14, 0),
                        end_time=time(16, 0),
                        status="pending",
                    ),
                ]
            )

        db.session.commit()

        print("Seed complete.")
        print(
            "Admin: admin@campusflow.edu / "
            "admin123"
        )
        print(
            "Student: student@campusflow.edu / "
            "student123"
        )


if __name__ == "__main__":
    seed()
