"""Form links service for token generation and validation."""

import secrets
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.form import FormLink


def generate_token() -> str:
    """Generate a URL-safe random token.

    Uses 16 bytes of cryptographically secure randomness,
    resulting in a 22-character base64url-encoded string.
    This provides 128 bits of entropy.
    """
    return secrets.token_urlsafe(16)


async def get_link_by_token(session: AsyncSession, token: str) -> FormLink | None:
    """Get a form link by its token."""
    result = await session.execute(
        select(FormLink).where(FormLink.token == token)
    )
    return result.scalars().first()


async def validate_token(session: AsyncSession, token: str) -> FormLink | None:
    """Validate a token and return the link if valid.

    Returns None if:
    - Token doesn't exist
    - Token has expired
    - Token is single-use and has already been used
    """
    link = await get_link_by_token(session, token)

    if not link:
        return None

    # Check expiration
    if link.expires_at and link.expires_at < datetime.utcnow():
        return None

    # Check single-use
    if link.is_single_use and link.used_at is not None:
        return None

    return link


async def mark_token_used(session: AsyncSession, link: FormLink) -> None:
    """Mark a token as used and increment the use count.

    For single-use tokens, this will prevent future use.
    For reusable tokens, this just tracks usage statistics.
    """
    if link.used_at is None:
        link.used_at = datetime.utcnow()
    link.use_count += 1
    session.add(link)
    await session.commit()


async def create_form_link(
    session: AsyncSession,
    form_id: UUID,
    contact_id: UUID,
    is_single_use: bool = False,
    expires_at: datetime | None = None,
) -> FormLink:
    """Create a new form link for a contact."""
    link = FormLink(
        form_id=form_id,
        contact_id=contact_id,
        token=generate_token(),
        is_single_use=is_single_use,
        expires_at=expires_at,
    )
    session.add(link)
    await session.commit()
    await session.refresh(link)
    return link


async def revoke_link(session: AsyncSession, link: FormLink) -> None:
    """Revoke (delete) a form link."""
    await session.delete(link)
    await session.commit()
