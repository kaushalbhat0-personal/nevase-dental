from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


def get_user(db: Session, user_id: UUID) -> User | None:
    return db.get(User, user_id)


def get_user_by_email(db: Session, email: str) -> User | None:
    # Case-insensitive email lookup
    stmt = select(User).where(User.email.ilike(email))
    return db.scalars(stmt).first()


def create_user(db: Session, user_data: dict[str, Any]) -> User:
    user = User(
        email=user_data["email"],
        hashed_password=user_data["hashed_password"],
    )
    if "role" in user_data and user_data["role"] is not None:
        user.role = user_data["role"]
    if user_data.get("tenant_id") is not None:
        user.tenant_id = user_data["tenant_id"]
    if user_data.get("force_password_reset") is True:
        user.force_password_reset = True
    if user_data.get("is_owner") is True:
        user.is_owner = True
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_user_tx(db: Session, user_data: dict[str, Any]) -> User:
    """
    Create a user within an existing transaction (no commit).
    """
    user = User(
        email=user_data["email"],
        hashed_password=user_data["hashed_password"],
    )
    if "role" in user_data and user_data["role"] is not None:
        user.role = user_data["role"]
    if user_data.get("tenant_id") is not None:
        user.tenant_id = user_data["tenant_id"]
    if user_data.get("force_password_reset") is True:
        user.force_password_reset = True
    if user_data.get("is_owner") is True:
        user.is_owner = True
    db.add(user)
    db.flush()
    db.refresh(user)
    return user
