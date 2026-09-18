from datetime import datetime, timedelta  # noqa: F401

import app as app_module


def book(
    client,
    resource_id,
    booking_date,
    start="10:00",
    end="11:00",
):
    return client.post(
        "/api/reservations",
        json={
            "resource_id": resource_id,
            "date": booking_date,
            "start_time": start,
            "end_time": end,
        },
    )


def test_instant_booking_is_confirmed(
    student_client,
    admin_client,
    create_resource,
    future_date,
    mock_mail,
):
    resource = create_resource(requires_approval=False)

    response = book(
        student_client,
        resource["id"],
        future_date,
    )

    assert response.status_code == 201
    reservation = response.get_json()["reservation"]
    assert reservation["status"] == "confirmed"

    mock_mail["send_booking_confirmation"].assert_called_once()


def test_resource_requiring_approval_creates_pending_booking(
    student_client,
    admin_client,
    create_resource,
    future_date,
    mock_mail,
):
    resource = create_resource(requires_approval=True)

    response = book(
        student_client,
        resource["id"],
        future_date,
    )

    assert response.status_code == 201
    assert response.get_json()["reservation"]["status"] == "pending"

    mock_mail["send_approval_email_to_user"].assert_called_once()
    mock_mail["send_approval_email_to_admin"].assert_called_once()


def test_pending_booking_blocks_overlapping_request(
    student_client,
    second_student_client,
    admin_client,
    create_resource,
    future_date,
):
    resource = create_resource(requires_approval=True)

    first = book(
        student_client,
        resource["id"],
        future_date,
        "10:00",
        "11:00",
    )
    assert first.status_code == 201
    assert first.get_json()["reservation"]["status"] == "pending"

    overlapping = book(
        second_student_client,
        resource["id"],
        future_date,
        "10:30",
        "11:30",
    )

    assert overlapping.status_code == 409
    data = overlapping.get_json()
    assert "overlaps" in data["error"].lower()
    assert isinstance(data["suggestions"], list)


def test_non_overlapping_slot_is_allowed(
    student_client,
    second_student_client,
    admin_client,
    create_resource,
    future_date,
):
    resource = create_resource()

    first = book(
        student_client,
        resource["id"],
        future_date,
        "10:00",
        "11:00",
    )
    assert first.status_code == 201

    second = book(
        second_student_client,
        resource["id"],
        future_date,
        "11:00",
        "12:00",
    )

    assert second.status_code == 201


def test_booking_over_maximum_duration_is_rejected(
    student_client,
    admin_client,
    create_resource,
    future_date,
):
    resource = create_resource(max_booking_minutes=60)

    response = book(
        student_client,
        resource["id"],
        future_date,
        "10:00",
        "11:30",
    )

    assert response.status_code == 400
    assert "maximum booking duration" in response.get_json()["error"].lower()


def test_booking_maintenance_resource_is_rejected(
    student_client,
    admin_client,
    create_resource,
    future_date,
):
    resource = create_resource()

    updated = admin_client.put(
        f"/api/resources/{resource['id']}",
        json={"status": "maintenance"},
    )
    assert updated.status_code == 200

    response = book(
        student_client,
        resource["id"],
        future_date,
    )

    assert response.status_code == 409
    assert "maintenance" in response.get_json()["error"].lower()


def test_daily_booking_limit(
    student_client,
    admin_client,
    create_resource,
    future_date,
):
    resource = create_resource(max_booking_minutes=60)

    for start, end in [
        ("09:30", "10:00"),
        ("10:00", "10:30"),
        ("10:30", "11:00"),
    ]:
        response = book(
            student_client,
            resource["id"],
            future_date,
            start,
            end,
        )
        assert response.status_code == 201

    fourth = book(
        student_client,
        resource["id"],
        future_date,
        "11:00",
        "12:00",
    )

    assert fourth.status_code == 429
    assert "daily booking limit" in fourth.get_json()["error"].lower()


def test_student_can_view_only_own_reservations(
    student_client,
    second_student_client,
    admin_client,
    create_resource,
    future_date,
):
    resource = create_resource()

    first = book(
        student_client,
        resource["id"],
        future_date,
        "10:00",
        "11:00",
    )
    assert first.status_code == 201

    second = book(
        second_student_client,
        resource["id"],
        future_date,
        "12:00",
        "13:00",
    )
    assert second.status_code == 201

    response = student_client.get("/api/reservations")

    assert response.status_code == 200
    reservations = response.get_json()["reservations"]
    assert len(reservations) == 1
    assert reservations[0]["start_time"] == "10:00"


def test_admin_can_approve_pending_reservation(
    student_client,
    admin_client,
    create_resource,
    future_date,
    mock_mail,
):
    resource = create_resource(requires_approval=True)

    created = book(
        student_client,
        resource["id"],
        future_date,
    )
    reservation_id = created.get_json()["reservation"]["id"]

    response = admin_client.post(
        f"/api/reservations/{reservation_id}/approve"
    )

    assert response.status_code == 200
    assert response.get_json()["reservation"]["status"] == "confirmed"
    mock_mail["send_approval_email"].assert_called_once()


def test_approving_confirmed_reservation_is_rejected(
    student_client,
    admin_client,
    create_resource,
    future_date,
):
    resource = create_resource(requires_approval=True)

    created = book(
        student_client,
        resource["id"],
        future_date,
    )
    reservation_id = created.get_json()["reservation"]["id"]

    first = admin_client.post(
        f"/api/reservations/{reservation_id}/approve"
    )
    assert first.status_code == 200

    second = admin_client.post(
        f"/api/reservations/{reservation_id}/approve"
    )
    assert second.status_code == 409


def test_admin_can_reject_pending_reservation(
    student_client,
    admin_client,
    create_resource,
    future_date,
    mock_mail,
):
    """
    This test exposes a bug in the uploaded app.py:
    reject_reservation() currently commits and sends mail but does not return
    a Flask response. Add a return jsonify(...) at the end of that route.
    """
    resource = create_resource(requires_approval=True)

    created = book(
        student_client,
        resource["id"],
        future_date,
    )
    reservation_id = created.get_json()["reservation"]["id"]

    response = admin_client.post(
        f"/api/reservations/{reservation_id}/reject"
    )

    assert response.status_code == 200
    assert response.get_json()["reservation"]["status"] == "rejected"
    mock_mail["send_rejection_email"].assert_called_once()


def test_student_can_cancel_own_booking(
    student_client,
    admin_client,
    create_resource,
    future_date,
    mock_mail,
):
    """
    This test exposes another bug in the uploaded app.py:
    cancel_reservation() currently has no return statement after sending mail.
    """
    resource = create_resource()

    created = book(
        student_client,
        resource["id"],
        future_date,
    )
    reservation_id = created.get_json()["reservation"]["id"]

    response = student_client.delete(
        f"/api/reservations/{reservation_id}"
    )

    assert response.status_code == 200
    assert response.get_json()["reservation"]["status"] == "cancelled"
    mock_mail["send_booking_cancellation"].assert_called_once()


def test_user_cannot_cancel_another_users_booking(
    student_client,
    second_student_client,
    admin_client,
    create_resource,
    future_date,
):
    resource = create_resource()

    created = book(
        student_client,
        resource["id"],
        future_date,
    )
    reservation_id = created.get_json()["reservation"]["id"]

    response = second_student_client.delete(
        f"/api/reservations/{reservation_id}"
    )

    assert response.status_code == 403


def test_successful_check_in(
    student_client,
    admin_client,
    create_resource,
    future_date,
    monkeypatch,
):
    resource = create_resource()

    created = book(
        student_client,
        resource["id"],
        future_date,
        "10:00",
        "11:00",
    )
    reservation_id = created.get_json()["reservation"]["id"]

    fixed_now = datetime.fromisoformat(f"{future_date}T09:55:00")

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now

    monkeypatch.setattr(app_module, "datetime", FixedDateTime)

    response = student_client.post(
        f"/api/reservations/{reservation_id}/check-in"
    )

    assert response.status_code == 200
    assert response.get_json()["reservation"]["checked_in_at"] is not None


def test_notifications_created_after_booking(
    student_client,
    admin_client,
    create_resource,
    future_date,
):
    resource = create_resource()

    created = book(
        student_client,
        resource["id"],
        future_date,
    )
    assert created.status_code == 201

    response = student_client.get("/api/notifications")

    assert response.status_code == 200
    notifications = response.get_json()["notifications"]
    assert len(notifications) >= 1
    assert "Booking confirmed" in notifications[0]["message"]
