from __future__ import annotations
import hashlib
import hmac
import secrets
from typing import Optional
from sqlalchemy.orm import Session
from ..models import User, Role
from ..config import SECRET_KEY


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hmac.compare_digest(hash_password(password), password_hash)


def ensure_default_admin(db: Session) -> None:
    if not db.query(User).filter_by(username="admin").first():
        user = User(username="admin", password_hash=hash_password("admin"), role=Role.admin)
        db.add(user)
        db.commit()


def generate_share_token() -> str:
    return secrets.token_urlsafe(16)


def can_apply_manager_discount(user: User) -> bool:
    return user.role in {Role.manager, Role.admin}