"""
Tests for user management endpoints: /api/v1/users (U1, U2, U3).
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import hash_password, create_access_token
from app.core.db import SessionLocal
from app.models.user import User

client = TestClient(app)


@pytest.fixture(scope="module")
def auth_tokens():
    """Create test admin and test examiner, return tokens."""
    db = SessionLocal()
    try:
        # Admin
        admin = db.query(User).filter(User.email == "user_mgmt_admin@osm.local").first()
        if not admin:
            admin = User(
                email="user_mgmt_admin@osm.local",
                password_hash=hash_password("AdminPass123!"),
                full_name="User Mgmt Admin",
                role="admin",
                is_active=True,
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)

        # Examiner
        examiner = db.query(User).filter(User.email == "user_mgmt_examiner@osm.local").first()
        if not examiner:
            examiner = User(
                email="user_mgmt_examiner@osm.local",
                password_hash=hash_password("ExaminerPass123!"),
                full_name="User Mgmt Examiner",
                role="examiner",
                is_active=True,
            )
            db.add(examiner)
            db.commit()
            db.refresh(examiner)

        admin_token, _ = create_access_token(admin.id, admin.role)
        examiner_token, _ = create_access_token(examiner.id, examiner.role)

        return {
            "admin_token": admin_token,
            "admin_id": admin.id,
            "examiner_token": examiner_token,
            "examiner_id": examiner.id,
        }
    finally:
        db.close()


def test_create_user_admin(auth_tokens):
    import uuid
    unique_email = f"new_examiner_{uuid.uuid4().hex[:6]}@osm.local"
    response = client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {auth_tokens['admin_token']}"},
        json={
            "email": unique_email,
            "full_name": "New Examiner",
            "role": "examiner",
            "password": "Password123!",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == unique_email
    assert data["role"] == "examiner"
    assert data["is_active"] is True


def test_create_user_duplicate_email(auth_tokens):
    response = client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {auth_tokens['admin_token']}"},
        json={
            "email": "user_mgmt_admin@osm.local",
            "full_name": "Duplicate Admin",
            "role": "admin",
            "password": "Password123!",
        },
    )
    assert response.status_code == 409
    data = response.json()
    assert data["error"]["code"] == "EMAIL_EXISTS"


def test_create_user_forbidden_for_non_admin(auth_tokens):
    response = client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {auth_tokens['examiner_token']}"},
        json={
            "email": "someone@osm.local",
            "full_name": "Someone",
            "role": "examiner",
            "password": "Password123!",
        },
    )
    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "FORBIDDEN"


def test_list_users(auth_tokens):
    response = client.get(
        "/api/v1/users?page=1&page_size=10",
        headers={"Authorization": f"Bearer {auth_tokens['admin_token']}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert len(data["items"]) > 0


def test_update_user(auth_tokens):
    response = client.patch(
        f"/api/v1/users/{auth_tokens['examiner_id']}",
        headers={"Authorization": f"Bearer {auth_tokens['admin_token']}"},
        json={"full_name": "Updated Examiner Name"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Updated Examiner Name"


def test_cannot_deactivate_self(auth_tokens):
    response = client.patch(
        f"/api/v1/users/{auth_tokens['admin_id']}",
        headers={"Authorization": f"Bearer {auth_tokens['admin_token']}"},
        json={"is_active": False},
    )
    assert response.status_code == 409
    data = response.json()
    assert data["error"]["code"] == "CANNOT_DEACTIVATE_SELF"
