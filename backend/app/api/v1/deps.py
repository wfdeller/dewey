"""API dependencies for authentication and authorization."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_session
from app.core.security import verify_token
from app.models.user import User, Role, UserRole
from app.models.tenant import Tenant

# Bearer token security scheme
security = HTTPBearer()


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


# Convenience type aliases
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentTenant = Annotated[Tenant, Depends(get_current_tenant)]
