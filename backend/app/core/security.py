"""Security utilities for authentication and authorization."""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.core.config import get_settings

settings = get_settings()

# Password hashing context using Argon2
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str  # User ID
    tenant_id: str
    exp: datetime
    type: str = "access"


class TokenPair(BaseModel):
    """Access and refresh token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash a password using Argon2."""
    return pwd_context.hash(password)


def create_access_token(
    user_id: UUID,
    tenant_id: UUID,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(
    user_id: UUID,
    tenant_id: UUID,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT refresh token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)

    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_token_pair(user_id: UUID, tenant_id: UUID) -> TokenPair:
    """Create both access and refresh tokens."""
    return TokenPair(
        access_token=create_access_token(user_id, tenant_id),
        refresh_token=create_refresh_token(user_id, tenant_id),
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}") from e


def verify_token(token: str, token_type: str = "access") -> TokenPayload:
    """Verify a token and return its payload."""
    payload = decode_token(token)

    if payload.get("type") != token_type:
        raise ValueError(f"Invalid token type: expected {token_type}")

    return TokenPayload(
        sub=payload["sub"],
        tenant_id=payload["tenant_id"],
        exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
        type=payload["type"],
    )
