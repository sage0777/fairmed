"""
Unit tests for user registration, login, and profile access.
"""

def test_register_new_user(client):
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Dr. Ananya Roy",
            "email": "ananya.roy@example.com",
            "password": "SecurePassword123!"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "ananya.roy@example.com"


def test_login_success(client):
    response = client.post(
        "/api/auth/login",
        json={
            "email": "pytest.user@fairmed.org",
            "password": "PytestPassword123!"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "pytest.user@fairmed.org"


def test_login_invalid_password(client):
    response = client.post(
        "/api/auth/login",
        json={
            "email": "pytest.user@fairmed.org",
            "password": "WrongPassword123!"
        }
    )
    assert response.status_code == 401


def test_get_profile(client, auth_headers):
    response = client.get("/api/auth/profile", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "pytest.user@fairmed.org"
