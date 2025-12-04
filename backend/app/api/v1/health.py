"""Health check endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def health() -> dict[str, str]:
    """API v1 health check."""
    return {"status": "healthy", "api_version": "v1"}
