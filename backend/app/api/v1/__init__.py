"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1 import (
    analytics,
    api_keys,
    auth,
    campaigns,
    categories,
    contacts,
    custom_fields,
    email_templates,
    forms,
    health,
    lov,
    messages,
    roles,
    tenants,
    users,
    voter_import,
    workflows,
)

router = APIRouter()

# Include all v1 routers
router.include_router(health.router, prefix="/health", tags=["Health"])
router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(tenants.router, prefix="/tenants", tags=["Tenants"])
router.include_router(messages.router, prefix="/messages", tags=["Messages"])
router.include_router(categories.router, prefix="/categories", tags=["Categories"])
router.include_router(contacts.router, prefix="/contacts", tags=["Contacts"])
router.include_router(custom_fields.router, prefix="/custom-fields", tags=["Custom Fields"])
router.include_router(campaigns.router, prefix="/campaigns", tags=["Campaigns"])
router.include_router(workflows.router, prefix="/workflows", tags=["Workflows"])
router.include_router(forms.router, prefix="/forms", tags=["Forms"])
router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
router.include_router(roles.router, prefix="/roles", tags=["Roles"])
router.include_router(users.router, prefix="/users", tags=["Users"])
router.include_router(api_keys.router, prefix="/api-keys", tags=["API Keys"])
router.include_router(email_templates.router, prefix="/email", tags=["Email Templates"])
router.include_router(lov.router, prefix="/lov", tags=["List of Values"])
router.include_router(voter_import.router, prefix="/voter-import", tags=["Voter Import"])
