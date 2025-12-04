"""Authentication service."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.security import (
    create_token_pair,
    hash_password,
    verify_password,
    verify_token,
    TokenPair,
)
from app.models.tenant import Tenant
from app.models.user import User, Role, UserRole, DEFAULT_ROLES


class AuthError(Exception):
    """Authentication error."""

    pass


class AuthService:
    """Service for authentication operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(
        self,
        email: str,
        password: str,
        name: str,
        tenant_name: str,
        tenant_slug: str,
    ) -> tuple[User, Tenant, TokenPair]:
        """
        Register a new user and tenant.

        Creates:
        - New tenant
        - Default roles for the tenant
        - User with owner role

        Returns:
            Tuple of (user, tenant, tokens)
        """
        # Check if email already exists
        result = await self.db.execute(select(User).where(User.email == email))
        if result.scalars().first():
            raise AuthError("Email already registered")

        # Check if tenant slug already exists
        result = await self.db.execute(
            select(Tenant).where(Tenant.slug == tenant_slug.lower())
        )
        if result.scalars().first():
            raise AuthError("Organization slug already taken")

        # Create tenant
        tenant = Tenant(
            name=tenant_name,
            slug=tenant_slug.lower(),
            subscription_tier="free",
        )
        self.db.add(tenant)
        await self.db.flush()  # Get tenant ID

        # Create default roles for the tenant
        roles_created: dict[str, Role] = {}
        for role_name, role_data in DEFAULT_ROLES.items():
            role = Role(
                tenant_id=tenant.id,
                name=role_name,
                description=role_data["description"],
                permissions=role_data["permissions"],
                is_system=True,
            )
            self.db.add(role)
            roles_created[role_name] = role

        await self.db.flush()  # Get role IDs

        # Create user
        user = User(
            tenant_id=tenant.id,
            email=email,
            name=name,
            password_hash=hash_password(password),
            is_active=True,
        )
        self.db.add(user)
        await self.db.flush()  # Get user ID

        # Assign owner role to user
        owner_role = roles_created["owner"]
        user_role = UserRole(
            user_id=user.id,
            role_id=owner_role.id,
        )
        self.db.add(user_role)

        await self.db.commit()
        await self.db.refresh(user)
        await self.db.refresh(tenant)

        # Generate tokens
        tokens = create_token_pair(user.id, tenant.id)

        return user, tenant, tokens

    async def login(self, email: str, password: str) -> tuple[User, Tenant, TokenPair]:
        """
        Authenticate a user.

        Returns:
            Tuple of (user, tenant, tokens)
        """
        # Find user by email
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalars().first()

        if not user:
            raise AuthError("Invalid email or password")

        if not user.password_hash:
            raise AuthError("Account uses SSO authentication")

        if not verify_password(password, user.password_hash):
            raise AuthError("Invalid email or password")

        if not user.is_active:
            raise AuthError("Account is disabled")

        # Get tenant
        result = await self.db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
        tenant = result.scalars().first()

        if not tenant:
            raise AuthError("Tenant not found")

        # Generate tokens
        tokens = create_token_pair(user.id, tenant.id)

        return user, tenant, tokens

    async def refresh_tokens(self, refresh_token: str) -> TokenPair:
        """
        Refresh access token using refresh token.

        Returns:
            New token pair
        """
        try:
            payload = verify_token(refresh_token, token_type="refresh")
        except ValueError as e:
            raise AuthError(str(e)) from e

        user_id = UUID(payload.sub)
        tenant_id = UUID(payload.tenant_id)

        # Verify user still exists and is active
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()

        if not user or not user.is_active:
            raise AuthError("User not found or inactive")

        return create_token_pair(user_id, tenant_id)

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalars().first()

    async def get_user_with_roles(self, user_id: UUID) -> tuple[User, list[Role]] | None:
        """Get user with roles loaded."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalars().first()

        if not user:
            return None

        # Load user roles
        roles_result = await self.db.execute(
            select(UserRole).where(UserRole.user_id == user_id)
        )
        user_roles = list(roles_result.scalars().all())

        # Load actual role objects
        roles: list[Role] = []
        for ur in user_roles:
            role_result = await self.db.execute(
                select(Role).where(Role.id == ur.role_id)
            )
            role = role_result.scalars().first()
            if role:
                roles.append(role)

        return user, roles

    async def get_tenant_by_id(self, tenant_id: UUID) -> Tenant | None:
        """Get tenant by ID."""
        result = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        return result.scalars().first()
