from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.auth import UserCreate


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: str | uuid.UUID) -> User | None:
    try:
        parsed_id = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))
    except ValueError:
        return None
    return db.query(User).filter(User.id == parsed_id).first()


def create_user(db: Session, user_in: UserCreate) -> User:
    user = User(
        full_name=user_in.full_name,
        email=str(user_in.email).lower(),
        hashed_password=hash_password(user_in.password),
        school_name=user_in.school_name,
        role="teacher",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, str(email).lower())
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
