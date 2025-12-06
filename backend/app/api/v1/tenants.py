"""Tenant management endpoints."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_session
from app.core.encryption import encrypt_value, decrypt_value, mask_api_key
from app.api.v1.deps import get_current_user, PermissionChecker
from app.models.tenant import Tenant
from app.models.user import User, Permissions
from app.models.lov import create_default_lov_entries
from app.services.ai.providers import get_provider
from app.services.ai.providers.base import AIProviderError

router = APIRouter()


class TenantCreateRequest(BaseModel):
    """Tenant creation schema."""

    name: str
    slug: str


class TenantResponse(BaseModel):
    """Tenant response schema."""

    id: UUID
    name: str
    slug: str
    subscription_tier: str


class TenantUpdate(BaseModel):
    """Tenant update schema."""

    name: str | None = None
    settings: dict | None = None


class WorkerSettingsResponse(BaseModel):
    """Worker settings response."""

    max_concurrent_jobs: int = Field(default=1, ge=1, le=10)
    job_timeout_seconds: int = Field(default=3600, ge=60, le=14400)
    max_retries: int = Field(default=3, ge=0, le=10)


class WorkerSettingsUpdate(BaseModel):
    """Worker settings update schema."""

    max_concurrent_jobs: int | None = Field(default=None, ge=1, le=10)
    job_timeout_seconds: int | None = Field(default=None, ge=60, le=14400)
    max_retries: int | None = Field(default=None, ge=0, le=10)


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    request: TenantCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> TenantResponse:
    """Create a new tenant (marketplace provisioning)."""
    # Check if slug already exists
    existing = await session.execute(
        select(Tenant).where(Tenant.slug == request.slug.lower().replace(" ", "-"))
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tenant with slug '{request.slug}' already exists",
        )

    # Create tenant
    tenant = Tenant(
        name=request.name,
        slug=request.slug,
    )
    session.add(tenant)
    await session.flush()  # Get tenant ID

    # Seed default LOV entries
    lov_entries = create_default_lov_entries(tenant.id)
    for entry in lov_entries:
        session.add(entry)

    await session.commit()
    await session.refresh(tenant)

    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        subscription_tier=tenant.subscription_tier,
    )


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> TenantResponse:
    """Get tenant details."""
    # TODO: Implement tenant retrieval
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Tenant retrieval not yet implemented",
    )


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: UUID,
    update: TenantUpdate,
    session: AsyncSession = Depends(get_session),
) -> TenantResponse:
    """Update tenant settings."""
    # TODO: Implement tenant update
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Tenant update not yet implemented",
    )


# =============================================================================
# Worker Settings Endpoints
# =============================================================================

# Default worker settings
DEFAULT_WORKER_SETTINGS = {
    "max_concurrent_jobs": 1,
    "job_timeout_seconds": 3600,
    "max_retries": 3,
}


@router.get("/settings/worker", response_model=WorkerSettingsResponse)
async def get_worker_settings(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WorkerSettingsResponse:
    """
    Get worker/job queue settings for the current tenant.

    Returns the configured worker settings with defaults applied.
    """
    # Get tenant
    result = await session.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalars().first()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    # Merge defaults with tenant settings
    worker_settings = {
        **DEFAULT_WORKER_SETTINGS,
        **tenant.settings.get("worker", {}),
    }

    return WorkerSettingsResponse(**worker_settings)


@router.patch("/settings/worker", response_model=WorkerSettingsResponse)
async def update_worker_settings(
    settings_update: WorkerSettingsUpdate,
    current_user: User = Depends(PermissionChecker(Permissions.SETTINGS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> WorkerSettingsResponse:
    """
    Update worker/job queue settings for the current tenant.

    Only provided fields will be updated. Requires SETTINGS_WRITE permission.

    Note: Changes to max_concurrent_jobs require a worker restart to take effect.
    """
    # Get tenant
    result = await session.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalars().first()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    # Get current worker settings or initialize
    current_settings = tenant.settings.get("worker", {})

    # Update only provided fields
    update_data = settings_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            current_settings[key] = value

    # Update tenant settings
    new_settings = {**tenant.settings, "worker": current_settings}
    tenant.settings = new_settings

    await session.commit()
    await session.refresh(tenant)

    # Return merged settings with defaults
    worker_settings = {
        **DEFAULT_WORKER_SETTINGS,
        **tenant.settings.get("worker", {}),
    }

    return WorkerSettingsResponse(**worker_settings)


# =============================================================================
# AI Configuration Endpoints
# =============================================================================

AIProviderType = Literal["claude", "openai", "azure_openai", "ollama"]
AIKeySourceType = Literal["platform", "tenant"]


class AIProviderConfigResponse(BaseModel):
    """AI provider configuration for display (keys masked)."""

    provider: str
    model: str | None = None
    api_key_set: bool = False
    api_key_masked: str | None = None
    # Azure OpenAI specific
    endpoint: str | None = None
    deployment: str | None = None
    api_version: str | None = None
    # Ollama specific
    base_url: str | None = None


class AIConfigResponse(BaseModel):
    """Full AI configuration response."""

    ai_provider: str
    ai_key_source: str
    ai_monthly_token_limit: int | None = None
    ai_tokens_used_this_month: int = 0
    subscription_tier: str
    providers: dict[str, AIProviderConfigResponse] = {}


class AIProviderConfigUpdate(BaseModel):
    """Update configuration for a specific provider."""

    api_key: str | None = None  # Will be encrypted before storage
    model: str | None = None
    # Azure OpenAI specific
    endpoint: str | None = None
    deployment: str | None = None
    api_version: str | None = None
    # Ollama specific
    base_url: str | None = None


class AIConfigUpdate(BaseModel):
    """Update AI configuration."""

    ai_provider: AIProviderType | None = None
    ai_key_source: AIKeySourceType | None = None


class AITestRequest(BaseModel):
    """Request to test AI connection."""

    provider: AIProviderType | None = None  # If None, test current provider


class AITestResponse(BaseModel):
    """Response from AI connection test."""

    success: bool
    provider: str
    model: str | None = None
    message: str
    latency_ms: int | None = None


class AIUsageResponse(BaseModel):
    """AI token usage statistics."""

    tokens_used_this_month: int
    monthly_limit: int | None = None
    percentage_used: float | None = None
    uses_platform_key: bool


# Default models for each provider
DEFAULT_MODELS = {
    "claude": "claude-3-haiku-20240307",
    "openai": "gpt-4-turbo",
    "azure_openai": "gpt-4",
    "ollama": "llama2",
}


@router.get("/settings/ai", response_model=AIConfigResponse)
async def get_ai_config(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AIConfigResponse:
    """
    Get AI configuration for the current tenant.

    Returns provider settings with API keys masked for security.
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

    # Build provider configurations with masked keys
    providers: dict[str, AIProviderConfigResponse] = {}
    for provider_name in ["claude", "openai", "azure_openai", "ollama"]:
        config = tenant.ai_provider_config.get(provider_name, {})
        encrypted_key = config.get("api_key_encrypted", "")

        # Decrypt and mask the key if set
        api_key_masked = None
        api_key_set = False
        if encrypted_key:
            try:
                decrypted = decrypt_value(encrypted_key)
                if decrypted:
                    api_key_masked = mask_api_key(decrypted)
                    api_key_set = True
            except Exception:
                pass  # Key couldn't be decrypted

        providers[provider_name] = AIProviderConfigResponse(
            provider=provider_name,
            model=config.get("model", DEFAULT_MODELS.get(provider_name)),
            api_key_set=api_key_set,
            api_key_masked=api_key_masked,
            endpoint=config.get("endpoint"),
            deployment=config.get("deployment"),
            api_version=config.get("api_version"),
            base_url=config.get("base_url"),
        )

    return AIConfigResponse(
        ai_provider=tenant.ai_provider,
        ai_key_source=tenant.ai_key_source,
        ai_monthly_token_limit=tenant.ai_monthly_token_limit,
        ai_tokens_used_this_month=tenant.ai_tokens_used_this_month,
        subscription_tier=tenant.subscription_tier,
        providers=providers,
    )


@router.patch("/settings/ai", response_model=AIConfigResponse)
async def update_ai_config(
    config_update: AIConfigUpdate,
    current_user: User = Depends(PermissionChecker(Permissions.SETTINGS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> AIConfigResponse:
    """
    Update AI configuration for the current tenant.

    Changes the active provider or key source. Requires SETTINGS_WRITE permission.
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

    # Update fields
    if config_update.ai_provider is not None:
        tenant.ai_provider = config_update.ai_provider
    if config_update.ai_key_source is not None:
        tenant.ai_key_source = config_update.ai_key_source

    await session.commit()
    await session.refresh(tenant)

    # Return full config (reuse get endpoint logic)
    return await get_ai_config(current_user, session)


@router.patch("/settings/ai/providers/{provider}", response_model=AIConfigResponse)
async def update_provider_config(
    provider: AIProviderType,
    config_update: AIProviderConfigUpdate,
    current_user: User = Depends(PermissionChecker(Permissions.SETTINGS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> AIConfigResponse:
    """
    Update configuration for a specific AI provider.

    API keys are encrypted before storage. Requires SETTINGS_WRITE permission.
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

    # Get or create provider config
    provider_config = tenant.ai_provider_config.get(provider, {})

    # Update fields
    if config_update.api_key is not None:
        if config_update.api_key == "":
            # Clear the API key
            provider_config.pop("api_key_encrypted", None)
        else:
            # Encrypt and store the new key
            provider_config["api_key_encrypted"] = encrypt_value(config_update.api_key)

    if config_update.model is not None:
        provider_config["model"] = config_update.model

    # Azure-specific fields
    if provider == "azure_openai":
        if config_update.endpoint is not None:
            provider_config["endpoint"] = config_update.endpoint
        if config_update.deployment is not None:
            provider_config["deployment"] = config_update.deployment
        if config_update.api_version is not None:
            provider_config["api_version"] = config_update.api_version

    # Ollama-specific fields
    if provider == "ollama":
        if config_update.base_url is not None:
            provider_config["base_url"] = config_update.base_url

    # Update tenant config (need to create new dict for SQLAlchemy to detect change)
    new_config = {**tenant.ai_provider_config, provider: provider_config}
    tenant.ai_provider_config = new_config

    await session.commit()
    await session.refresh(tenant)

    return await get_ai_config(current_user, session)


@router.post("/settings/ai/test", response_model=AITestResponse)
async def test_ai_connection(
    request: AITestRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AITestResponse:
    """
    Test AI provider connection.

    Sends a simple prompt to verify the provider is configured correctly.
    """
    import time

    result = await session.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalars().first()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    # Use specified provider or current provider
    provider_name = request.provider or tenant.ai_provider

    try:
        # Get provider instance
        provider = get_provider(tenant)

        # Send test prompt
        start_time = time.time()
        response = await provider.complete(
            prompt="Reply with exactly: 'Connection successful'",
            system_prompt="You are a test assistant. Reply exactly as instructed.",
            max_tokens=50,
            temperature=0,
        )
        latency_ms = int((time.time() - start_time) * 1000)

        return AITestResponse(
            success=True,
            provider=provider_name,
            model=response.model,
            message=f"Successfully connected to {provider_name}",
            latency_ms=latency_ms,
        )

    except AIProviderError as e:
        return AITestResponse(
            success=False,
            provider=provider_name,
            model=None,
            message=str(e),
            latency_ms=None,
        )
    except Exception as e:
        return AITestResponse(
            success=False,
            provider=provider_name,
            model=None,
            message=f"Connection failed: {str(e)}",
            latency_ms=None,
        )


@router.get("/settings/ai/usage", response_model=AIUsageResponse)
async def get_ai_usage(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AIUsageResponse:
    """
    Get AI token usage statistics for the current tenant.
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

    # Calculate percentage if limit exists
    percentage = None
    if tenant.ai_monthly_token_limit:
        percentage = round(
            (tenant.ai_tokens_used_this_month / tenant.ai_monthly_token_limit) * 100, 2
        )

    return AIUsageResponse(
        tokens_used_this_month=tenant.ai_tokens_used_this_month,
        monthly_limit=tenant.ai_monthly_token_limit,
        percentage_used=percentage,
        uses_platform_key=tenant.uses_platform_key(),
    )
