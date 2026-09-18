def test_student_cannot_open_approval_queue(student_client):
    response = student_client.get("/api/approvals")
    assert response.status_code == 403


def test_admin_approval_queue_lists_pending_requests(
    student_client,
    admin_client,
    create_resource,
    future_date,
):
    resource = create_resource(requires_approval=True)

    created = student_client.post(
        "/api/reservations",
        json={
            "resource_id": resource["id"],
            "date": future_date,
            "start_time": "10:00",
            "end_time": "11:00",
        },
    )
    assert created.status_code == 201

    response = admin_client.get("/api/approvals")

    assert response.status_code == 200
    reservations = response.get_json()["reservations"]
    assert len(reservations) == 1
    assert reservations[0]["status"] == "pending"


def test_student_cannot_open_dashboard(student_client):
    response = student_client.get("/api/dashboard")
    assert response.status_code == 403


def test_dashboard_reports_resource_totals(
    admin_client,
    create_resource,
):
    create_resource(name="Printer")
    create_resource(name="Camera", type="Camera", category="Media")

    response = admin_client.get("/api/dashboard")

    assert response.status_code == 200
    data = response.get_json()
    assert data["totals"]["total_resources"] == 2
    assert "utilization_rate" in data
    assert "pending_approvals" in data["totals"]
    assert "no_shows" in data["totals"]
