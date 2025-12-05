"""Category management endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_session
from app.api.v1.deps import PermissionChecker
from app.models.user import User, Permissions
from app.models.category import (
    Category,
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
)

router = APIRouter()


class CategoryListResponse(BaseModel):
    """Paginated category list response."""

    items: list[CategoryRead]
    total: int


class CategoryTreeNode(CategoryRead):
    """Category with children for tree display."""

    children: list["CategoryTreeNode"] = []


# =============================================================================
# Category Endpoints
# =============================================================================


@router.get("", response_model=CategoryListResponse)
async def list_categories(
    include_inactive: bool = Query(False, description="Include inactive categories"),
    current_user: User = Depends(PermissionChecker(Permissions.CATEGORIES_READ)),
    session: AsyncSession = Depends(get_session),
) -> CategoryListResponse:
    """
    List all categories for the current tenant.

    Returns a flat list of categories. Use /tree endpoint for hierarchical view.
    """
    query = select(Category).where(Category.tenant_id == current_user.tenant_id)

    if not include_inactive:
        query = query.where(Category.is_active == True)

    query = query.order_by(Category.sort_order, Category.name)

    result = await session.execute(query)
    categories = result.scalars().all()

    return CategoryListResponse(
        items=[CategoryRead.model_validate(c) for c in categories],
        total=len(categories),
    )


@router.get("/tree", response_model=list[CategoryTreeNode])
async def get_category_tree(
    include_inactive: bool = Query(False, description="Include inactive categories"),
    current_user: User = Depends(PermissionChecker(Permissions.CATEGORIES_READ)),
    session: AsyncSession = Depends(get_session),
) -> list[CategoryTreeNode]:
    """
    Get categories as a hierarchical tree structure.

    Returns only root categories (parent_id=null) with nested children.
    """
    query = select(Category).where(Category.tenant_id == current_user.tenant_id)

    if not include_inactive:
        query = query.where(Category.is_active == True)

    query = query.order_by(Category.sort_order, Category.name)

    result = await session.execute(query)
    categories = result.scalars().all()

    # Build tree from flat list
    by_id = {c.id: CategoryTreeNode(**CategoryRead.model_validate(c).model_dump()) for c in categories}

    roots = []
    for cat in categories:
        node = by_id[cat.id]
        if cat.parent_id and cat.parent_id in by_id:
            by_id[cat.parent_id].children.append(node)
        else:
            roots.append(node)

    return roots


@router.get("/{category_id}", response_model=CategoryRead)
async def get_category(
    category_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.CATEGORIES_READ)),
    session: AsyncSession = Depends(get_session),
) -> CategoryRead:
    """Get a specific category by ID."""
    result = await session.execute(
        select(Category).where(
            Category.id == category_id,
            Category.tenant_id == current_user.tenant_id,
        )
    )
    category = result.scalars().first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    return CategoryRead.model_validate(category)


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(
    request: CategoryCreate,
    current_user: User = Depends(PermissionChecker(Permissions.CATEGORIES_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> CategoryRead:
    """Create a new category."""
    # Check for duplicate name within tenant
    result = await session.execute(
        select(Category).where(
            Category.tenant_id == current_user.tenant_id,
            Category.name == request.name,
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name already exists",
        )

    # Validate parent exists if specified
    if request.parent_id:
        parent_result = await session.execute(
            select(Category).where(
                Category.id == request.parent_id,
                Category.tenant_id == current_user.tenant_id,
            )
        )
        if not parent_result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent category not found",
            )

    category = Category(
        tenant_id=current_user.tenant_id,
        **request.model_dump(),
    )
    session.add(category)
    await session.commit()
    await session.refresh(category)

    return CategoryRead.model_validate(category)


@router.patch("/{category_id}", response_model=CategoryRead)
async def update_category(
    category_id: UUID,
    request: CategoryUpdate,
    current_user: User = Depends(PermissionChecker(Permissions.CATEGORIES_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> CategoryRead:
    """Update a category."""
    result = await session.execute(
        select(Category).where(
            Category.id == category_id,
            Category.tenant_id == current_user.tenant_id,
        )
    )
    category = result.scalars().first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    # Check name uniqueness if changing
    if request.name and request.name != category.name:
        name_result = await session.execute(
            select(Category).where(
                Category.tenant_id == current_user.tenant_id,
                Category.name == request.name,
                Category.id != category_id,
            )
        )
        if name_result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category with this name already exists",
            )

    # Validate parent if changing
    if request.parent_id is not None:
        if request.parent_id == category_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category cannot be its own parent",
            )
        if request.parent_id:
            parent_result = await session.execute(
                select(Category).where(
                    Category.id == request.parent_id,
                    Category.tenant_id == current_user.tenant_id,
                )
            )
            if not parent_result.scalars().first():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Parent category not found",
                )

    # Apply updates
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)

    await session.commit()
    await session.refresh(category)

    return CategoryRead.model_validate(category)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.CATEGORIES_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Delete a category.

    Categories with children cannot be deleted - delete children first or reassign them.
    """
    result = await session.execute(
        select(Category).where(
            Category.id == category_id,
            Category.tenant_id == current_user.tenant_id,
        )
    )
    category = result.scalars().first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    # Check for children
    children_result = await session.execute(
        select(Category).where(Category.parent_id == category_id)
    )
    if children_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete category with children. Delete or reassign children first.",
        )

    await session.delete(category)
    await session.commit()


@router.post("/{category_id}/reorder", response_model=CategoryRead)
async def reorder_category(
    category_id: UUID,
    new_sort_order: int = Query(..., ge=0),
    new_parent_id: UUID | None = Query(None),
    current_user: User = Depends(PermissionChecker(Permissions.CATEGORIES_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> CategoryRead:
    """
    Reorder a category (change sort order and/or parent).

    Used for drag-and-drop reordering in the UI.
    """
    result = await session.execute(
        select(Category).where(
            Category.id == category_id,
            Category.tenant_id == current_user.tenant_id,
        )
    )
    category = result.scalars().first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    # Validate new parent if specified
    if new_parent_id:
        if new_parent_id == category_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category cannot be its own parent",
            )
        parent_result = await session.execute(
            select(Category).where(
                Category.id == new_parent_id,
                Category.tenant_id == current_user.tenant_id,
            )
        )
        if not parent_result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent category not found",
            )

    category.sort_order = new_sort_order
    category.parent_id = new_parent_id

    await session.commit()
    await session.refresh(category)

    return CategoryRead.model_validate(category)
