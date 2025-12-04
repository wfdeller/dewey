"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1 import auth, health, messages, tenants

router = APIRouter()

# Include all v1 routers
router.include_router(health.router, prefix="/health", tags=["Health"])
router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(tenants.router, prefix="/tenants", tags=["Tenants"])
router.include_router(messages.router, prefix="/messages", tags=["Messages"])
