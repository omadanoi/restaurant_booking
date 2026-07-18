import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError

# --- Password hashing -------------------------------------------------------

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        # Malformed hash in the DB (e.g. seeded test data) — treat as no match.
        return False


# --- Access tokens (JWT) ----------------------------------------------------

def create_access_token(user_id: uuid.UUID, role: str) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "jti": secrets.token_hex(8),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired.") from None
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid token.") from None
    if payload.get("type") != "access":
        raise AuthenticationError("Invalid token type.")
    return payload


# --- Refresh tokens (opaque, stored hashed) ---------------------------------

def generate_refresh_token() -> str:
    """256 bits of randomness; the raw value goes only to the client."""
    return secrets.token_urlsafe(32)


def hash_refresh_token(raw_token: str) -> str:
    """SHA-256 (not bcrypt): refresh tokens are high-entropy random strings,
    so brute-forcing a leaked hash is infeasible and a fast hash lets us
    look tokens up by exact hash match.
    """
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
