"""API dependencies for authentication and authorization."""

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_session
from app.core.security import verify_token
from app.core.redis import check_rate_limit
from app.models.user import User, Role, UserRole
from app.models.tenant import Tenant
from app.models.api_key import APIKey

# Bearer token security scheme
security = HTTPBearer()
# Optional bearer for endpoints that accept both JWT and API key
optional_security = HTTPBearer(auto_error=False)


@dataclass
class AuthContext:
    """
    Authentication context that can represent either a user session or API key.

    Provides unified access to tenant_id and permissions for both auth methods.
    """
    tenant_id: UUID
    user: User | None = None  # Set for JWT auth
    api_key: APIKey | None = None  # Set for API key auth

    @property
    def is_api_key(self) -> bool:
        """Check if this is an API key authentication."""
        return self.api_key is not None

    @property
    def is_user(self) -> bool:
        """Check if this is a user JWT authentication."""
        return self.user is not None

    def has_scope(self, scope: str) -> bool:
        """Check if the auth context has a specific scope/permission."""
        if self.api_key:
            return self.api_key.has_scope(scope)
        # For users, we don't check scopes here (use PermissionChecker)
        return True


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    session: AsyncSession = Depends(get_session),
) -> User:
    """
    Dependency to get the current authenticated user from JWT token.

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials

    try:
        payload = verify_token(token, token_type="access")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = UUID(payload.sub)

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Dependency to ensure user is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return current_user


async def get_api_key_auth(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(optional_security)],
    session: AsyncSession = Depends(get_session),
) -> APIKey:
    """
    Dependency to authenticate via API key.

    Expects Authorization header: Bearer dwy_xxxxx

    Raises:
        HTTPException: If API key is invalid, expired, or IP not allowed
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # Check if it looks like an API key (starts with dwy_)
    if not token.startswith("dwy_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Hash the key and look it up
    key_hash = APIKey.hash_key(token)

    result = await session.execute(
        select(APIKey).where(APIKey.key_hash == key_hash)
    )
    api_key = result.scalars().first()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if expired
    if api_key.is_expired():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check IP restrictions
    client_ip = request.client.host if request.client else "unknown"
    if not api_key.is_ip_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"IP address {client_ip} not allowed for this API key",
        )

    # Check rate limit
    rate_key = f"api_key:{api_key.id}"
    allowed, remaining, reset_seconds = await check_rate_limit(
        key=rate_key,
        limit=api_key.rate_limit,
        window_seconds=60,  # 1 minute window
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {reset_seconds} seconds.",
            headers={
                "X-RateLimit-Limit": str(api_key.rate_limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_seconds),
                "Retry-After": str(reset_seconds),
            },
        )

    # Update usage tracking
    api_key.last_used_at = datetime.utcnow()
    api_key.usage_count += 1
    await session.commit()

    return api_key


async def get_auth_context(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(optional_security)],
    session: AsyncSession = Depends(get_session),
) -> AuthContext:
    """
    Unified authentication that accepts either JWT token or API key.

    Returns an AuthContext with either user or api_key populated.

    Usage:
        @router.get("/data")
        async def get_data(
            auth: AuthContext = Depends(get_auth_context)
        ):
            # auth.tenant_id is always available
            # auth.user is set for JWT auth
            # auth.api_key is set for API key auth
            ...
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # Check if it's an API key (starts with dwy_)
    if token.startswith("dwy_"):
        api_key = await get_api_key_auth(request, credentials, session)
        return AuthContext(tenant_id=api_key.tenant_id, api_key=api_key)

    # Otherwise, treat as JWT
    try:
        payload = verify_token(token, token_type="access")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = UUID(payload.sub)

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthContext(tenant_id=user.tenant_id, user=user)


async def get_current_tenant(
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
) -> Tenant:
    """
    Dependency to get the current user's tenant.
    """
    result = await session.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalars().first()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    return tenant


class PermissionChecker:
    """
    Dependency class to check if user has required permission(s).

    Usage:
        @router.get("/protected")
        async def protected_route(
            user: User = Depends(PermissionChecker("messages:read"))
        ):
            ...

        @router.get("/admin")
        async def admin_route(
            user: User = Depends(PermissionChecker(["users:read", "users:write"]))
        ):
            ...
    """

    def __init__(self, required_permissions: str | list[str], require_all: bool = True):
        """
        Initialize permission checker.

        Args:
            required_permissions: Permission(s) required to access the route
            require_all: If True, user must have ALL permissions. If False, ANY permission.
        """
        if isinstance(required_permissions, str):
            self.required_permissions = [required_permissions]
        else:
            self.required_permissions = required_permissions
        self.require_all = require_all

    async def __call__(
        self,
        current_user: Annotated[User, Depends(get_current_user)],
        session: AsyncSession = Depends(get_session),
    ) -> User:
        """Check if user has required permissions."""
        # Load user roles
        roles_result = await session.execute(
            select(UserRole).where(UserRole.user_id == current_user.id)
        )
        user_roles = roles_result.scalars().all()

        # Collect all permissions
        all_permissions: set[str] = set()
        for ur in user_roles:
            role_result = await session.execute(select(Role).where(Role.id == ur.role_id))
            role = role_result.scalars().first()
            if role:
                all_permissions.update(role.permissions)

        # Check permissions
        if self.require_all:
            has_permission = all(p in all_permissions for p in self.required_permissions)
        else:
            has_permission = any(p in all_permissions for p in self.required_permissions)

        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return current_user


class ScopeChecker:
    """
    Dependency class to check if API key has required scope(s).

    Usage:
        @router.get("/messages")
        async def list_messages(
            auth: AuthContext = Depends(ScopeChecker("messages:read"))
        ):
            ...
    """

    def __init__(self, required_scopes: str | list[str], require_all: bool = True):
        """
        Initialize scope checker.

        Args:
            required_scopes: Scope(s) required to access the route
            require_all: If True, key must have ALL scopes. If False, ANY scope.
        """
        if isinstance(required_scopes, str):
            self.required_scopes = [required_scopes]
        else:
            self.required_scopes = required_scopes
        self.require_all = require_all

    async def __call__(
        self,
        request: Request,
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(optional_security)],
        session: AsyncSession = Depends(get_session),
    ) -> AuthContext:
        """Check if auth context has required scopes."""
        auth = await get_auth_context(request, credentials, session)

        # For user auth, scopes are always satisfied (use PermissionChecker for users)
        if auth.is_user:
            return auth

        # For API key auth, check scopes
        if auth.api_key:
            if self.require_all:
                has_scope = all(auth.api_key.has_scope(s) for s in self.required_scopes)
            else:
                has_scope = any(auth.api_key.has_scope(s) for s in self.required_scopes)

            if not has_scope:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"API key lacks required scope(s): {', '.join(self.required_scopes)}",
                )

        return auth


# Convenience type aliases
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentTenant = Annotated[Tenant, Depends(get_current_tenant)]
CurrentAuthContext = Annotated[AuthContext, Depends(get_auth_context)]
CurrentAPIKey = Annotated[APIKey, Depends(get_api_key_auth)]
