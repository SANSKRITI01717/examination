"""
Tests for authentication endpoints: /api/v1/auth/login and /api/v1/auth/me (A1, A2).
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import hash_password, create_access_token
from app.core.db import SessionLocal
from app.models.user import User

client = TestClient(app)


@pytest.fixture(scope="module")
def setup_test_users():
    """Ensure test users exist in database."""
    db = SessionLocal()
    try:
        # 1. Active Admin
        admin = db.query(User).filter(User.email == "test_admin@osm.local").first()
        if not admin:
            admin = User(
                email="test_admin@osm.local",
                password_hash=hash_password("AdminPass123!"),
                full_name="Test Admin",
                role="admin",
                is_active=True,
            )
            db.add(admin)

        # 2. Inactive User
        inactive = db.query(User).filter(User.email == "inactive@osm.local").first()
        if not inactive:
            inactive = User(
                email="inactive@osm.local",
                password_hash=hash_password("InactivePass123!"),
                full_name="Inactive User",
                role="examiner",
                is_active=False,
            )
            db.add(inactive)

        db.commit()
    finally:
        db.close()


def test_login_success(setup_test_users):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "test_admin@osm.local", "password": "AdminPass123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0
    assert data["user"]["email"] == "test_admin@osm.local"
    assert data["user"]["role"] == "admin"


def test_login_invalid_password(setup_test_users):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "test_admin@osm.local", "password": "WrongPassword123!"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_nonexistent_email(setup_test_users):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@osm.local", "password": "SomePassword123!"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_inactive_user(setup_test_users):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "inactive@osm.local", "password": "InactivePass123!"},
    )
    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "USER_INACTIVE"


def test_get_me_success(setup_test_users):
    # Log in first to get token
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "test_admin@osm.local", "password": "AdminPass123!"},
    )
    token = login_resp.json()["access_token"]

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    user_data = response.json()
    assert user_data["email"] == "test_admin@osm.local"
    assert user_data["role"] == "admin"


def test_get_me_missing_token():
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "UNAUTHENTICATED"


def test_get_me_invalid_token():
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_garbage_token"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "UNAUTHENTICATED"
