"""Role management endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from app.core.database import get_session
from app.api.v1.deps import CurrentUser, PermissionChecker
from app.models.user import User, Role, UserRole, Permissions, DEFAULT_ROLES
from app.schemas.roles import (
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    RoleListResponse,
    PermissionInfo,
    PermissionListResponse,
)

router = APIRouter()


# =============================================================================
# Permission Metadata
# =============================================================================

PERMISSION_METADATA = {
    Permissions.MESSAGES_READ: {
        "name": "Read Messages",
        "description": "View messages and their analysis",
        "category": "Messages",
    },
    Permissions.MESSAGES_WRITE: {
        "name": "Write Messages",
        "description": "Create and edit messages",
        "category": "Messages",
    },
    Permissions.MESSAGES_DELETE: {
        "name": "Delete Messages",
        "description": "Delete messages",
        "category": "Messages",
    },
    Permissions.MESSAGES_ASSIGN: {
        "name": "Assign Messages",
        "description": "Assign messages to categories and users",
        "category": "Messages",
    },
    Permissions.CONTACTS_READ: {
        "name": "Read Contacts",
        "description": "View contacts and their history",
        "category": "Contacts",
    },
    Permissions.CONTACTS_WRITE: {
        "name": "Write Contacts",
        "description": "Create and edit contacts",
        "category": "Contacts",
    },
    Permissions.CONTACTS_DELETE: {
        "name": "Delete Contacts",
        "description": "Delete contacts",
        "category": "Contacts",
    },
    Permissions.CATEGORIES_READ: {
        "name": "Read Categories",
        "description": "View categories",
        "category": "Categories",
    },
    Permissions.CATEGORIES_WRITE: {
        "name": "Write Categories",
        "description": "Create and edit categories",
        "category": "Categories",
    },
    Permissions.WORKFLOWS_READ: {
        "name": "Read Workflows",
        "description": "View workflows",
        "category": "Workflows",
    },
    Permissions.WORKFLOWS_WRITE: {
        "name": "Write Workflows",
        "description": "Create and edit workflows",
        "category": "Workflows",
    },
    Permissions.WORKFLOWS_EXECUTE: {
        "name": "Execute Workflows",
        "description": "Manually trigger workflows",
        "category": "Workflows",
    },
    Permissions.ANALYTICS_READ: {
        "name": "Read Analytics",
        "description": "View analytics dashboards",
        "category": "Analytics",
    },
    Permissions.ANALYTICS_EXPORT: {
        "name": "Export Analytics",
        "description": "Export analytics data",
        "category": "Analytics",
    },
    Permissions.FORMS_READ: {
        "name": "Read Forms",
        "description": "View forms and submissions",
        "category": "Forms",
    },
    Permissions.FORMS_WRITE: {
        "name": "Write Forms",
        "description": "Create and edit forms",
        "category": "Forms",
    },
    Permissions.CAMPAIGNS_READ: {
        "name": "Read Campaigns",
        "description": "View detected campaigns",
        "category": "Campaigns",
    },
    Permissions.CAMPAIGNS_WRITE: {
        "name": "Write Campaigns",
        "description": "Manage campaigns",
        "category": "Campaigns",
    },
    Permissions.SETTINGS_READ: {
        "name": "Read Settings",
        "description": "View tenant settings",
        "category": "Settings",
    },
    Permissions.SETTINGS_WRITE: {
        "name": "Write Settings",
        "description": "Modify tenant settings",
        "category": "Settings",
    },
    Permissions.USERS_READ: {
        "name": "Read Users",
        "description": "View users in the organization",
        "category": "Users",
    },
    Permissions.USERS_WRITE: {
        "name": "Write Users",
        "description": "Invite and manage users",
        "category": "Users",
    },
    Permissions.ROLES_WRITE: {
        "name": "Manage Roles",
        "description": "Create and edit custom roles",
        "category": "Roles",
    },
    Permissions.API_KEYS_MANAGE: {
        "name": "Manage API Keys",
        "description": "Create and revoke API keys",
        "category": "API",
    },
    Permissions.INTEGRATIONS_MANAGE: {
        "name": "Manage Integrations",
        "description": "Configure integrations",
        "category": "Integrations",
    },
    Permissions.BILLING_MANAGE: {
        "name": "Manage Billing",
        "description": "View and manage billing",
        "category": "Billing",
    },
}


# =============================================================================
# Role Endpoints
# =============================================================================


@router.get("", response_model=RoleListResponse)
async def list_roles(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> RoleListResponse:
    """
    List all roles for the current tenant.

    Returns both system roles and custom roles.
    """
    result = await session.execute(
        select(Role).where(Role.tenant_id == current_user.tenant_id).order_by(Role.name)
    )
    roles = result.scalars().all()

    return RoleListResponse(
        roles=[RoleResponse.model_validate(role) for role in roles],
        total=len(roles),
    )


@router.get("/permissions", response_model=PermissionListResponse)
async def list_permissions() -> PermissionListResponse:
    """
    List all available permissions.

    Returns metadata about each permission for UI display.
    """
    permissions = [
        PermissionInfo(
            key=key,
            name=meta["name"],
            description=meta["description"],
            category=meta["category"],
        )
        for key, meta in PERMISSION_METADATA.items()
    ]

    # Sort by category then name
    permissions.sort(key=lambda p: (p.category, p.name))

    return PermissionListResponse(permissions=permissions)


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> RoleResponse:
    """
    Get a specific role by ID.
    """
    result = await session.execute(
        select(Role).where(
            Role.id == role_id,
            Role.tenant_id == current_user.tenant_id,
        )
    )
    role = result.scalars().first()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    return RoleResponse.model_validate(role)


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    request: RoleCreate,
    current_user: User = Depends(PermissionChecker(Permissions.ROLES_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> RoleResponse:
    """
    Create a new custom role.

    System roles cannot be created via API.
    """
    # Check if role name already exists for this tenant
    existing = await session.execute(
        select(Role).where(
            Role.tenant_id == current_user.tenant_id,
            Role.name == request.name,
        )
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role '{request.name}' already exists",
        )

    # Validate permissions
    valid_permissions = set(PERMISSION_METADATA.keys())
    invalid_permissions = set(request.permissions) - valid_permissions
    if invalid_permissions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid permissions: {', '.join(invalid_permissions)}",
        )

    # Create role
    role = Role(
        tenant_id=current_user.tenant_id,
        name=request.name,
        description=request.description,
        permissions=request.permissions,
        azure_ad_group_id=request.azure_ad_group_id,
        is_system=False,
    )
    session.add(role)
    await session.commit()
    await session.refresh(role)

    return RoleResponse.model_validate(role)


@router.patch("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: UUID,
    request: RoleUpdate,
    current_user: User = Depends(PermissionChecker(Permissions.ROLES_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> RoleResponse:
    """
    Update a role's permissions or metadata.

    System role names cannot be changed, but their permissions can be customized.
    """
    result = await session.execute(
        select(Role).where(
            Role.id == role_id,
            Role.tenant_id == current_user.tenant_id,
        )
    )
    role = result.scalars().first()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    # System roles cannot have their name changed
    if role.is_system and request.name and request.name != role.name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change name of system role",
        )

    # Check for name conflict if changing name
    if request.name and request.name != role.name:
        existing = await session.execute(
            select(Role).where(
                Role.tenant_id == current_user.tenant_id,
                Role.name == request.name,
            )
        )
        if existing.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role '{request.name}' already exists",
            )
        role.name = request.name

    # Validate permissions if provided
    if request.permissions is not None:
        valid_permissions = set(PERMISSION_METADATA.keys())
        invalid_permissions = set(request.permissions) - valid_permissions
        if invalid_permissions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid permissions: {', '.join(invalid_permissions)}",
            )
        role.permissions = request.permissions

    # Update other fields
    if request.description is not None:
        role.description = request.description
    if request.azure_ad_group_id is not None:
        role.azure_ad_group_id = request.azure_ad_group_id or None

    await session.commit()
    await session.refresh(role)

    return RoleResponse.model_validate(role)


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.ROLES_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Delete a custom role.

    System roles cannot be deleted.
    """
    result = await session.execute(
        select(Role).where(
            Role.id == role_id,
            Role.tenant_id == current_user.tenant_id,
        )
    )
    role = result.scalars().first()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete system role",
        )

    # Check if any users have this role
    user_count_result = await session.execute(
        select(func.count()).select_from(UserRole).where(UserRole.role_id == role_id)
    )
    user_count = user_count_result.scalar()

    if user_count and user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete role: {user_count} user(s) have this role assigned",
        )

    await session.delete(role)
    await session.commit()


@router.post("/{role_id}/reset", response_model=RoleResponse)
async def reset_system_role(
    role_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.ROLES_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> RoleResponse:
    """
    Reset a system role to its default permissions.

    Only applicable to system roles.
    """
    result = await session.execute(
        select(Role).where(
            Role.id == role_id,
            Role.tenant_id == current_user.tenant_id,
        )
    )
    role = result.scalars().first()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    if not role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only system roles can be reset",
        )

    # Get default permissions for this role
    if role.name not in DEFAULT_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown system role: {role.name}",
        )

    default_config = DEFAULT_ROLES[role.name]
    role.permissions = default_config["permissions"]
    role.description = default_config["description"]

    await session.commit()
    await session.refresh(role)

    return RoleResponse.model_validate(role)
