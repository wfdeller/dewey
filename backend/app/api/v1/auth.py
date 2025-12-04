"""Authentication endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    RefreshRequest,
    UserResponse,
    AzureAuthUrlResponse,
    AzureCallbackRequest,
    AzureLinkRequest,
)
from app.services.auth import AuthService, AuthError
from app.services.azure_auth import AzureAuthService, AzureAuthError
from app.api.v1.deps import get_current_user
from app.models.user import User

router = APIRouter()
settings = get_settings()


# =============================================================================
# Password Authentication
# =============================================================================


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """
    Register a new user and tenant.

    Creates a new tenant organization and user account with owner role.
    """
    auth_service = AuthService(session)

    try:
        user, tenant, tokens = await auth_service.register(
            email=request.email,
            password=request.password,
            name=request.name,
            tenant_name=request.tenant_name,
            tenant_slug=request.tenant_slug,
        )
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """
    Authenticate user with email/password and return tokens.
    """
    auth_service = AuthService(session)

    try:
        user, tenant, tokens = await auth_service.login(
            email=request.email,
            password=request.password,
        )
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """
    Refresh access token using refresh token.
    """
    auth_service = AuthService(session)

    try:
        tokens = await auth_service.refresh_tokens(request.refresh_token)
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )


# =============================================================================
# Azure AD Authentication
# =============================================================================


@router.get("/azure/login", response_model=AzureAuthUrlResponse)
async def azure_login(
    session: AsyncSession = Depends(get_session),
) -> AzureAuthUrlResponse:
    """
    Get Azure AD authorization URL for SSO login.

    Frontend should redirect user to the returned `auth_url`.
    Store the `state` value to verify on callback.
    """
    if not settings.azure_client_id:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Azure AD authentication is not configured",
        )

    azure_service = AzureAuthService(session)

    try:
        auth_url, state = azure_service.get_auth_url()
    except AzureAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    return AzureAuthUrlResponse(auth_url=auth_url, state=state)


@router.get("/azure/callback")
async def azure_callback(
    code: str = Query(..., description="Authorization code from Azure AD"),
    state: str = Query(..., description="CSRF state"),
    session: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    """
    Handle Azure AD OAuth callback.

    This endpoint receives the authorization code from Azure AD after
    user authentication. It exchanges the code for tokens and redirects
    to the frontend with our JWT tokens.

    In production, the frontend URL should be configurable.
    """
    azure_service = AzureAuthService(session)

    try:
        user, tenant, tokens = await azure_service.handle_callback(code, state)
    except AzureAuthError as e:
        # Redirect to frontend with error
        error_url = f"{settings.cors_origins[0]}/auth/error?error={str(e)}"
        return RedirectResponse(url=error_url)

    # Redirect to frontend with tokens
    # Frontend should extract tokens from URL fragment and store them
    success_url = (
        f"{settings.cors_origins[0]}/auth/callback"
        f"#access_token={tokens.access_token}"
        f"&refresh_token={tokens.refresh_token}"
        f"&token_type=bearer"
    )
    return RedirectResponse(url=success_url)


@router.post("/azure/callback", response_model=TokenResponse)
async def azure_callback_post(
    request: AzureCallbackRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """
    Handle Azure AD OAuth callback (POST variant).

    Alternative to GET callback for SPAs that handle the redirect themselves.
    Frontend exchanges the authorization code for tokens directly.
    """
    azure_service = AzureAuthService(session)

    try:
        user, tenant, tokens = await azure_service.handle_callback(
            request.code, request.state
        )
    except AzureAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )


@router.post("/azure/link", response_model=UserResponse)
async def link_azure_account(
    request: AzureLinkRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    """
    Link Azure AD account to existing user.

    Allows users who registered with email/password to also
    sign in with their Azure AD account.
    """
    azure_service = AzureAuthService(session)
    auth_service = AuthService(session)

    try:
        user = await azure_service.link_azure_account(
            current_user, request.code
        )
    except AzureAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Get updated user info
    result = await auth_service.get_user_with_roles(user.id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user, roles = result
    tenant = await auth_service.get_tenant_by_id(user.tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    role_names = [role.name for role in roles]
    all_permissions: set[str] = set()
    for role in roles:
        all_permissions.update(role.permissions)

    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        is_active=user.is_active,
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        tenant_slug=tenant.slug,
        roles=role_names,
        permissions=sorted(all_permissions),
    )


# =============================================================================
# User Info
# =============================================================================


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    """
    Get current authenticated user information.
    """
    auth_service = AuthService(session)

    # Load user with roles
    result = await auth_service.get_user_with_roles(current_user.id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user, roles = result

    # Get tenant
    tenant = await auth_service.get_tenant_by_id(user.tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    # Collect roles and permissions
    role_names = [role.name for role in roles]
    all_permissions: set[str] = set()
    for role in roles:
        all_permissions.update(role.permissions)

    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        is_active=user.is_active,
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        tenant_slug=tenant.slug,
        roles=role_names,
        permissions=sorted(all_permissions),
    )
