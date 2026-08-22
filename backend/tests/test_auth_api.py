from conftest import KNOWN_PASSWORDS, client


def test_login_with_valid_credentials_returns_token():
    response = client.post(
        "/auth/login", json={"username": "admin", "password": KNOWN_PASSWORDS["admin"]}
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]
    assert payload["user"]["username"] == "admin"
    assert payload["user"]["role"] == "admin"


def test_login_with_wrong_password_is_rejected():
    response = client.post(
        "/auth/login", json={"username": "admin", "password": "wrong-password"}
    )
    assert response.status_code == 401


def test_login_with_unknown_username_is_rejected():
    response = client.post(
        "/auth/login", json={"username": "nobody", "password": "irrelevant"}
    )
    assert response.status_code == 401


def test_me_returns_current_user_with_valid_token():
    login_response = client.post(
        "/auth/login", json={"username": "books_lead", "password": KNOWN_PASSWORDS["books_lead"]}
    )
    token = login_response.json()["access_token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["username"] == "books_lead"
    assert payload["role"] == "books_team_lead"


def test_me_without_token_is_rejected():
    response = client.get("/auth/me")
    assert response.status_code == 403


def test_me_with_invalid_token_is_rejected():
    response = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401
