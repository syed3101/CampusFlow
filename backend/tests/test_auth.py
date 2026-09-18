def test_me_returns_none_when_logged_out(client):
    response = client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.get_json() == {"user": None}


def test_student_registration_logs_user_in(client):
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Alice",
            "email": "alice@test.com",
            "password": "secret123",
            "role": "student",
        },
    )

    assert response.status_code == 201
    assert response.get_json()["user"]["email"] == "alice@test.com"
    assert response.get_json()["user"]["role"] == "student"

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.get_json()["user"]["email"] == "alice@test.com"


def test_duplicate_email_is_rejected(client):
    payload = {
        "name": "Alice",
        "email": "alice@test.com",
        "password": "secret123",
        "role": "student",
    }

    first = client.post("/api/auth/register", json=payload)
    second = client.post("/api/auth/register", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409


def test_registration_requires_six_character_password(client):
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Alice",
            "email": "alice@test.com",
            "password": "123",
            "role": "student",
        },
    )

    assert response.status_code == 400


def test_admin_registration_rejects_wrong_invite_code(client):
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Admin",
            "email": "admin@test.com",
            "password": "admin123",
            "role": "admin",
            "invite_code": "WRONG",
        },
    )

    assert response.status_code == 403


def test_login_and_logout(client):
    client.post(
        "/api/auth/register",
        json={
            "name": "Alice",
            "email": "alice@test.com",
            "password": "secret123",
            "role": "student",
        },
    )
    client.post("/api/auth/logout")

    bad_login = client.post(
        "/api/auth/login",
        json={
            "email": "alice@test.com",
            "password": "wrong-password",
        },
    )
    assert bad_login.status_code == 401

    good_login = client.post(
        "/api/auth/login",
        json={
            "email": "alice@test.com",
            "password": "secret123",
        },
    )
    assert good_login.status_code == 200

    logout = client.post("/api/auth/logout")
    assert logout.status_code == 200

    me = client.get("/api/auth/me")
    assert me.get_json()["user"] is None
