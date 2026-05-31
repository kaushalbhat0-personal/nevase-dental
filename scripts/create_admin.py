import sys
import os
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(__file__), '..', 'backend', '.env')
load_dotenv(dotenv_path)

from app.core.database import SessionLocal
from app.core.security import hash_password
from sqlalchemy import text


def create_admin():
    db = SessionLocal()
    try:
        existing = db.execute(
            text("SELECT id, email FROM users WHERE email = 'admin@nevase.com'")
        ).fetchone()

        if existing:
            print(f"Admin already exists: {existing.email}")
            return

        columns = db.execute(
            text("SELECT column_name FROM information_schema.columns WHERE table_name = 'users'")
        ).fetchall()
        print("Users table columns:", [c[0] for c in columns])

        admin_id = uuid.uuid4()
        hashed = hash_password("Admin@123")

        db.execute(
            text("""
                INSERT INTO users (id, email, hashed_password, full_name, role, is_active)
                VALUES (:id, :email, :password, :name, :role, true)
            """),
            {
                "id": str(admin_id),
                "email": "admin@nevase.com",
                "password": hashed,
                "name": "Clinic Admin",
                "role": "admin",
            }
        )
        db.commit()
        print("Admin created successfully!")
        print("Email: admin@nevase.com")
        print("Password: Admin@123")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
