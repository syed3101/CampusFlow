def test_resources_require_login(client):
    response = client.get("/api/resources")
    assert response.status_code == 401


def test_student_cannot_create_resource(student_client):
    response = student_client.post(
        "/api/resources",
        json={
            "name": "Camera",
            "type": "Camera",
            "category": "Media",
            "lab": "Media Lab",
        },
    )

    assert response.status_code == 403


def test_admin_can_create_and_list_resource(admin_client, create_resource):
    resource = create_resource()

    response = admin_client.get("/api/resources")

    assert response.status_code == 200
    resources = response.get_json()["resources"]
    assert len(resources) == 1
    assert resources[0]["id"] == resource["id"]
    assert resources[0]["name"] == "Prusa MK4"


def test_resource_search_and_filters(admin_client, create_resource):
    create_resource(
        name="Prusa Printer",
        type="3D Printer",
        category="Prototyping",
        lab="Innovation Lab",
    )
    create_resource(
        name="DSLR Camera",
        type="Camera",
        category="Media",
        lab="Media Lab",
    )

    search = admin_client.get("/api/resources?q=printer")
    assert search.status_code == 200
    assert [r["name"] for r in search.get_json()["resources"]] == [
        "Prusa Printer"
    ]

    lab_filter = admin_client.get(
        "/api/resources",
        query_string={"lab": "Media Lab"},
    )
    assert lab_filter.status_code == 200
    assert [r["name"] for r in lab_filter.get_json()["resources"]] == [
        "DSLR Camera"
    ]


def test_admin_can_mark_resource_under_maintenance(
    admin_client,
    create_resource,
):
    resource = create_resource()

    response = admin_client.put(
        f"/api/resources/{resource['id']}",
        json={"status": "maintenance"},
    )

    assert response.status_code == 200
    updated = response.get_json()["resource"]
    assert updated["admin_status"] == "maintenance"
    assert updated["status"] == "maintenance"


def test_invalid_resource_status_is_rejected(
    admin_client,
    create_resource,
):
    resource = create_resource()

    response = admin_client.put(
        f"/api/resources/{resource['id']}",
        json={"status": "broken-forever"},
    )

    assert response.status_code == 400


def test_resource_availability_returns_active_slots(
    student_client,
    admin_client,
    create_resource,
    future_date,
):
    resource = create_resource()

    booking = student_client.post(
        "/api/reservations",
        json={
            "resource_id": resource["id"],
            "date": future_date,
            "start_time": "10:00",
            "end_time": "11:00",
        },
    )
    assert booking.status_code == 201

    response = student_client.get(
        f"/api/resources/{resource['id']}/availability",
        query_string={"date": future_date},
    )

    assert response.status_code == 200
    slots = response.get_json()["bookings"]
    assert len(slots) == 1
    assert slots[0]["start_time"] == "10:00"
    assert slots[0]["end_time"] == "11:00"
