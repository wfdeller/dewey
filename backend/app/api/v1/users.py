"""User management endpoints."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from app.core.database import get_session
from app.api.v1.deps import PermissionChecker
from app.models.user import User, Role, UserRole, Permissions
from app.schemas.roles import (
    UserListItem,
    UserListResponse,
    UserDetailResponse,
    UserRoleResponse,
    UserRoleAssignment,
    UserUpdateRequest,
)

router = APIRouter()


# =============================================================================
# User List & Detail
# =============================================================================


@router.get("", response_model=UserListResponse)
async def list_users(
    current_user: User = Depends(PermissionChecker(Permissions.USERS_READ)),
    session: AsyncSession = Depends(get_session),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
) -> UserListResponse:
    """
    List all users in the current tenant.
    """
    # Build base query
    query = select(User).where(User.tenant_id == current_user.tenant_id)

    # Apply filters
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (User.email.ilike(search_filter)) | (User.name.ilike(search_filter))
        )
    if is_active is not None:
        query = query.where(User.is_active == is_active)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination and ordering
    query = query.order_by(User.name).offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    users = result.scalars().all()

    # Load roles for each user
    user_items = []
    for user in users:
        roles_result = await session.execute(
            select(Role)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user.id)
        )
        roles = roles_result.scalars().all()

        user_items.append(
            UserListItem(
                id=user.id,
                email=user.email,
                name=user.name,
                is_active=user.is_active,
                azure_ad_oid=user.azure_ad_oid,
                roles=[r.name for r in roles],
                created_at=user.created_at,
                last_login_at=None,  # TODO: Track last login
            )
        )

    return UserListResponse(users=user_items, total=total)


@router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.USERS_READ)),
    session: AsyncSession = Depends(get_session),
) -> UserDetailResponse:
    """
    Get detailed information about a specific user.
    """
    result = await session.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == current_user.tenant_id,
        )
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Load roles with assignment details
    user_roles_result = await session.execute(
        select(UserRole, Role)
        .join(Role, Role.id == UserRole.role_id)
        .where(UserRole.user_id == user.id)
    )
    user_roles_data = user_roles_result.all()

    # Build role responses and collect permissions
    role_responses = []
    all_permissions: set[str] = set()

    for user_role, role in user_roles_data:
        role_responses.append(
            UserRoleResponse(
                role_id=role.id,
                role_name=role.name,
                assigned_at=user_role.assigned_at,
                assigned_by=user_role.assigned_by,
            )
        )
        all_permissions.update(role.permissions)

    return UserDetailResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        is_active=user.is_active,
        azure_ad_oid=user.azure_ad_oid,
        tenant_id=user.tenant_id,
        roles=role_responses,
        permissions=sorted(all_permissions),
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.patch("/{user_id}", response_model=UserDetailResponse)
async def update_user(
    user_id: UUID,
    request: UserUpdateRequest,
    current_user: User = Depends(PermissionChecker(Permissions.USERS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> UserDetailResponse:
    """
    Update a user's profile.
    """
    result = await session.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == current_user.tenant_id,
        )
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Update fields
    if request.name is not None:
        user.name = request.name
    if request.is_active is not None:
        # Prevent deactivating yourself
        if user.id == current_user.id and not request.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate your own account",
            )
        user.is_active = request.is_active

    await session.commit()
    await session.refresh(user)

    # Return full user detail
    return await get_user(user_id, current_user, session)


# =============================================================================
# User Role Management
# =============================================================================


@router.get("/{user_id}/roles", response_model=list[UserRoleResponse])
async def get_user_roles(
    user_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.USERS_READ)),
    session: AsyncSession = Depends(get_session),
) -> list[UserRoleResponse]:
    """
    Get roles assigned to a specific user.
    """
    # Verify user exists and belongs to tenant
    user_result = await session.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == current_user.tenant_id,
        )
    )
    if not user_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Load roles
    result = await session.execute(
        select(UserRole, Role)
        .join(Role, Role.id == UserRole.role_id)
        .where(UserRole.user_id == user_id)
    )
    roles_data = result.all()

    return [
        UserRoleResponse(
            role_id=role.id,
            role_name=role.name,
            assigned_at=user_role.assigned_at,
            assigned_by=user_role.assigned_by,
        )
        for user_role, role in roles_data
    ]


@router.post("/{user_id}/roles", response_model=UserRoleResponse, status_code=status.HTTP_201_CREATED)
async def assign_role_to_user(
    user_id: UUID,
    request: UserRoleAssignment,
    current_user: User = Depends(PermissionChecker(Permissions.USERS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> UserRoleResponse:
    """
    Assign a role to a user.
    """
    # Verify user exists and belongs to tenant
    user_result = await session.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == current_user.tenant_id,
        )
    )
    target_user = user_result.scalars().first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Verify role exists and belongs to tenant
    role_result = await session.execute(
        select(Role).where(
            Role.id == request.role_id,
            Role.tenant_id == current_user.tenant_id,
        )
    )
    role = role_result.scalars().first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    # Check if already assigned
    existing_result = await session.execute(
        select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == request.role_id,
        )
    )
    if existing_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role already assigned to user",
        )

    # Create assignment
    user_role = UserRole(
        user_id=user_id,
        role_id=request.role_id,
        assigned_at=datetime.utcnow(),
        assigned_by=current_user.id,
    )
    session.add(user_role)
    await session.commit()

    return UserRoleResponse(
        role_id=role.id,
        role_name=role.name,
        assigned_at=user_role.assigned_at,
        assigned_by=user_role.assigned_by,
    )


@router.delete("/{user_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_role_from_user(
    user_id: UUID,
    role_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.USERS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Remove a role from a user.
    """
    # Verify user exists and belongs to tenant
    user_result = await session.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == current_user.tenant_id,
        )
    )
    target_user = user_result.scalars().first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Verify role exists and belongs to tenant
    role_result = await session.execute(
        select(Role).where(
            Role.id == role_id,
            Role.tenant_id == current_user.tenant_id,
        )
    )
    role = role_result.scalars().first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    # Find the assignment
    assignment_result = await session.execute(
        select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id,
        )
    )
    assignment = assignment_result.scalars().first()

    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not assigned to user",
        )

    # Prevent removing owner role from yourself if you're the last owner
    if role.name == "owner" and user_id == current_user.id:
        # Check if there are other owners
        owner_count_result = await session.execute(
            select(func.count())
            .select_from(UserRole)
            .join(Role, Role.id == UserRole.role_id)
            .where(
                Role.tenant_id == current_user.tenant_id,
                Role.name == "owner",
            )
        )
        owner_count = owner_count_result.scalar() or 0

        if owner_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last owner role",
            )

    await session.delete(assignment)
    await session.commit()


@router.put("/{user_id}/roles", response_model=list[UserRoleResponse])
async def set_user_roles(
    user_id: UUID,
    role_ids: list[UUID],
    current_user: User = Depends(PermissionChecker(Permissions.USERS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> list[UserRoleResponse]:
    """
    Set all roles for a user (replaces existing roles).
    """
    # Verify user exists and belongs to tenant
    user_result = await session.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == current_user.tenant_id,
        )
    )
    target_user = user_result.scalars().first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Verify all roles exist and belong to tenant
    roles_result = await session.execute(
        select(Role).where(
            Role.id.in_(role_ids),
            Role.tenant_id == current_user.tenant_id,
        )
    )
    roles = {role.id: role for role in roles_result.scalars().all()}

    if len(roles) != len(role_ids):
        missing = set(role_ids) - set(roles.keys())
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Roles not found: {', '.join(str(r) for r in missing)}",
        )

    # Check if removing owner role from self
    if user_id == current_user.id:
        # Get current owner role id
        owner_role_result = await session.execute(
            select(Role).where(
                Role.tenant_id == current_user.tenant_id,
                Role.name == "owner",
            )
        )
        owner_role = owner_role_result.scalars().first()

        if owner_role and owner_role.id not in role_ids:
            # Check if there are other owners
            owner_count_result = await session.execute(
                select(func.count())
                .select_from(UserRole)
                .join(Role, Role.id == UserRole.role_id)
                .where(
                    Role.tenant_id == current_user.tenant_id,
                    Role.name == "owner",
                    UserRole.user_id != current_user.id,
                )
            )
            owner_count = owner_count_result.scalar() or 0

            if owner_count == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot remove owner role: no other owners exist",
                )

    # Delete existing roles
    existing_result = await session.execute(
        select(UserRole).where(UserRole.user_id == user_id)
    )
    for existing in existing_result.scalars().all():
        await session.delete(existing)

    # Add new roles
    now = datetime.utcnow()
    role_responses = []

    for role_id in role_ids:
        role = roles[role_id]
        user_role = UserRole(
            user_id=user_id,
            role_id=role_id,
            assigned_at=now,
            assigned_by=current_user.id,
        )
        session.add(user_role)
        role_responses.append(
            UserRoleResponse(
                role_id=role.id,
                role_name=role.name,
                assigned_at=now,
                assigned_by=current_user.id,
            )
        )

    await session.commit()

    return role_responses
