import os
from datetime import date, timedelta
from unittest.mock import Mock

import pytest

# IMPORTANT:
# These variables are set BEFORE app.py is imported because app.py reads
# configuration while the module is imported.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "pytest-secret-key"
os.environ["ADMIN_INVITE_CODE"] = "TEST-ADMIN-CODE"
os.environ["DAILY_BOOKING_LIMIT"] = "3"
os.environ["CHECKIN_EARLY_MINUTES"] = "15"
os.environ["NO_SHOW_GRACE_MINUTES"] = "15"
os.environ.pop("FRONTEND_ORIGIN", None)

import app as app_module
from models import db


@pytest.fixture()
def app():
    test_app = app_module.create_app()
    test_app.config.update(
        TESTING=True,
        SECRET_KEY="pytest-secret-key",
    )

    with test_app.app_context():
        db.drop_all()
        db.create_all()

    yield test_app

    with test_app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def mock_mail(monkeypatch):
    """
    Never send real Gmail messages from pytest.

    app.py imports the mail functions directly, therefore we patch the names
    inside the app module instead of patching mail_services.py.
    """
    names = [
        "send_booking_confirmation",
        "send_booking_cancellation",
        "send_approval_email_to_admin",
        "send_approval_email_to_user",
        "send_approval_email",
        "send_rejection_email",
    ]

    mocks = {}
    for name in names:
        mocked = Mock(return_value=True)
        monkeypatch.setattr(app_module, name, mocked)
        mocks[name] = mocked

    return mocks


def register_student(client, email="student@test.com", name="Test Student"):
    response = client.post(
        "/api/auth/register",
        json={
            "name": name,
            "email": email,
            "password": "student123",
            "role": "student",
        },
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()["user"]


def register_admin(client, email="admin@test.com", name="Test Admin"):
    response = client.post(
        "/api/auth/register",
        json={
            "name": name,
            "email": email,
            "password": "admin123",
            "role": "admin",
            "invite_code": "TEST-ADMIN-CODE",
        },
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()["user"]


@pytest.fixture()
def student_client(app):
    test_client = app.test_client()
    register_student(test_client)
    return test_client


@pytest.fixture()
def second_student_client(app):
    test_client = app.test_client()
    register_student(
        test_client,
        email="student2@test.com",
        name="Second Student",
    )
    return test_client


@pytest.fixture()
def admin_client(app):
    test_client = app.test_client()
    register_admin(test_client)
    return test_client


@pytest.fixture()
def create_resource(admin_client):
    def _create(**overrides):
        payload = {
            "name": "Prusa MK4",
            "type": "3D Printer",
            "category": "Prototyping",
            "lab": "Innovation Lab",
            "description": "Test resource",
            "max_booking_minutes": 180,
            "requires_approval": False,
        }
        payload.update(overrides)

        response = admin_client.post(
            "/api/resources",
            json=payload,
        )
        assert response.status_code == 201, response.get_json()
        return response.get_json()["resource"]

    return _create


@pytest.fixture()
def future_date():
    return (date.today() + timedelta(days=1)).isoformat()  # noqa: DTZ011
