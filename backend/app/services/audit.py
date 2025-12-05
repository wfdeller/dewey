"""Audit logging service for tracking system activity."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.user import User


class AuditService:
    """Service for creating audit log entries."""

    def __init__(self, session: AsyncSession, tenant_id: UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def log(
        self,
        entity_type: str,
        action: str,
        description: str,
        entity_id: UUID | None = None,
        entity_name: str | None = None,
        user: User | None = None,
        user_id: UUID | None = None,
        user_email: str | None = None,
        user_name: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        changes: dict | None = None,
        extra_data: dict | None = None,
    ) -> AuditLog:
        """
        Create an audit log entry.

        Args:
            entity_type: Type of entity (e.g., "contact", "message", "campaign")
            action: Action performed (e.g., "created", "updated", "deleted")
            description: Human-readable description
            entity_id: ID of the affected entity
            entity_name: Display name of the entity
            user: User object (will extract id, email, name)
            user_id: User ID (if user object not provided)
            user_email: User email (if user object not provided)
            user_name: User name (if user object not provided)
            ip_address: Request IP address
            user_agent: Request user agent
            changes: Dict of field changes {field: {old, new}}
            extra_data: Additional context data

        Returns:
            Created AuditLog entry
        """
        # Extract user info from User object if provided
        if user:
            user_id = user.id
            user_email = user.email
            user_name = user.name

        audit_log = AuditLog(
            tenant_id=self.tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            action=action,
            description=description,
            user_id=user_id,
            user_email=user_email,
            user_name=user_name,
            ip_address=ip_address,
            user_agent=user_agent,
            changes=changes,
            extra_data=extra_data,
        )

        self.session.add(audit_log)
        # Note: We don't commit here - caller should manage transaction
        return audit_log

    async def log_create(
        self,
        entity_type: str,
        entity_id: UUID,
        entity_name: str,
        user: User | None = None,
        ip_address: str | None = None,
        extra_data: dict | None = None,
    ) -> AuditLog:
        """Log an entity creation."""
        return await self.log(
            entity_type=entity_type,
            action="created",
            description=f"{entity_type.title()} '{entity_name}' created",
            entity_id=entity_id,
            entity_name=entity_name,
            user=user,
            ip_address=ip_address,
            extra_data=extra_data,
        )

    async def log_update(
        self,
        entity_type: str,
        entity_id: UUID,
        entity_name: str,
        changes: dict,
        user: User | None = None,
        ip_address: str | None = None,
        extra_data: dict | None = None,
    ) -> AuditLog:
        """Log an entity update with field changes."""
        # Build description from changes
        changed_fields = list(changes.keys())
        if len(changed_fields) == 1:
            desc = f"{entity_type.title()} '{entity_name}' {changed_fields[0]} updated"
        else:
            desc = f"{entity_type.title()} '{entity_name}' updated ({len(changed_fields)} fields)"

        return await self.log(
            entity_type=entity_type,
            action="updated",
            description=desc,
            entity_id=entity_id,
            entity_name=entity_name,
            user=user,
            ip_address=ip_address,
            changes=changes,
            extra_data=extra_data,
        )

    async def log_delete(
        self,
        entity_type: str,
        entity_id: UUID,
        entity_name: str,
        user: User | None = None,
        ip_address: str | None = None,
        extra_data: dict | None = None,
    ) -> AuditLog:
        """Log an entity deletion."""
        return await self.log(
            entity_type=entity_type,
            action="deleted",
            description=f"{entity_type.title()} '{entity_name}' deleted",
            entity_id=entity_id,
            entity_name=entity_name,
            user=user,
            ip_address=ip_address,
            extra_data=extra_data,
        )

    async def log_import(
        self,
        entity_type: str,
        count: int,
        source: str,
        user: User | None = None,
        ip_address: str | None = None,
        extra_data: dict | None = None,
    ) -> AuditLog:
        """Log a bulk import operation."""
        return await self.log(
            entity_type=entity_type,
            action="imported",
            description=f"{count} {entity_type}(s) imported from {source}",
            user=user,
            ip_address=ip_address,
            extra_data=extra_data,
        )


def compute_changes(old_values: dict, new_values: dict) -> dict:
    """
    Compute the differences between old and new values.

    Args:
        old_values: Dict of original field values
        new_values: Dict of new field values

    Returns:
        Dict of changes in format {field: {old: value, new: value}}
    """
    changes = {}

    # Check all fields in new_values
    for field, new_val in new_values.items():
        old_val = old_values.get(field)

        # Skip if values are the same
        if old_val == new_val:
            continue

        # Skip None -> None
        if old_val is None and new_val is None:
            continue

        # Record the change
        changes[field] = {
            "old": _serialize_value(old_val),
            "new": _serialize_value(new_val),
        }

    return changes


def _serialize_value(value: Any) -> Any:
    """Serialize a value for JSON storage."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_serialize_value(v) for v in value]
    if isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    # Fallback to string representation
    return str(value)
