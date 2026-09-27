"""
Seed initial administrator user into the database if not already present.
Usage:
    python backend/scripts/seed_admin.py
"""
import os
import sys
from pathlib import Path

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models.user import User


def seed_admin() -> None:
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@osm.local").strip().lower()
    admin_password = os.environ.get("ADMIN_PASSWORD", "AdminPassword123!")
    admin_name = os.environ.get("ADMIN_NAME", "System Administrator").strip()

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == admin_email).first()
        if existing:
            print(f"Admin user already exists: {admin_email} (ID: {existing.id})")
            return

        admin_user = User(
            email=admin_email,
            password_hash=hash_password(admin_password),
            full_name=admin_name,
            role="admin",
            is_active=True,
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        print(f"Successfully created admin user: {admin_email} (ID: {admin_user.id})")
    finally:
        db.close()


if __name__ == "__main__":
    seed_admin()
