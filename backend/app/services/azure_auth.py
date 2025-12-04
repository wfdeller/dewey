"""Azure AD authentication service using MSAL."""

import secrets
from dataclasses import dataclass
from uuid import UUID

import msal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import get_settings
from app.core.security import create_token_pair, TokenPair
from app.models.tenant import Tenant
from app.models.user import User, Role, UserRole, DEFAULT_ROLES


class AzureAuthError(Exception):
    """Azure AD authentication error."""

    pass


@dataclass
class AzureUserInfo:
    """User information from Azure AD token."""

    oid: str  # Azure AD Object ID (unique per user)
    email: str
    name: str
    tenant_id: str  # Azure AD Tenant ID
    preferred_username: str | None = None
    given_name: str | None = None
    family_name: str | None = None


class AzureAuthService:
    """Service for Azure AD authentication."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self._msal_app: msal.ConfidentialClientApplication | None = None

    @property
    def msal_app(self) -> msal.ConfidentialClientApplication:
        """Get or create MSAL confidential client application."""
        if self._msal_app is None:
            if not self.settings.azure_client_id or not self.settings.azure_client_secret:
                raise AzureAuthError("Azure AD is not configured")

            # Use "common" for multi-tenant or specific tenant ID
            authority = f"https://login.microsoftonline.com/{self.settings.azure_tenant_id or 'common'}"

            self._msal_app = msal.ConfidentialClientApplication(
                client_id=self.settings.azure_client_id,
                client_credential=self.settings.azure_client_secret,
                authority=authority,
            )
        return self._msal_app

    def get_auth_url(self, state: str | None = None) -> tuple[str, str]:
        """
        Generate Azure AD authorization URL.

        Args:
            state: Optional CSRF state. If not provided, one will be generated.

        Returns:
            Tuple of (auth_url, state)
        """
        if state is None:
            state = secrets.token_urlsafe(32)

        # Scopes for OpenID Connect + basic profile
        scopes = ["openid", "profile", "email", "User.Read"]

        auth_url = self.msal_app.get_authorization_request_url(
            scopes=scopes,
            state=state,
            redirect_uri=self.settings.azure_redirect_uri,
        )

        return auth_url, state

    async def handle_callback(
        self, code: str, state: str
    ) -> tuple[User, Tenant, TokenPair]:
        """
        Handle Azure AD callback after user authentication.

        Args:
            code: Authorization code from Azure AD
            state: CSRF state (should be validated by caller)

        Returns:
            Tuple of (user, tenant, tokens)
        """
        # Exchange authorization code for tokens
        scopes = ["openid", "profile", "email", "User.Read"]

        result = self.msal_app.acquire_token_by_authorization_code(
            code=code,
            scopes=scopes,
            redirect_uri=self.settings.azure_redirect_uri,
        )

        if "error" in result:
            raise AzureAuthError(
                f"Failed to acquire token: {result.get('error_description', result.get('error'))}"
            )

        # Extract user info from ID token claims
        id_token_claims = result.get("id_token_claims", {})
        user_info = self._extract_user_info(id_token_claims)

        # Find or create user
        user, tenant = await self._find_or_create_user(user_info)

        # Generate our own JWT tokens
        tokens = create_token_pair(user.id, tenant.id)

        return user, tenant, tokens

    def _extract_user_info(self, claims: dict) -> AzureUserInfo:
        """Extract user information from Azure AD ID token claims."""
        oid = claims.get("oid")
        if not oid:
            raise AzureAuthError("Missing user object ID in token")

        # Email can be in different claims depending on Azure AD config
        email = (
            claims.get("email")
            or claims.get("preferred_username")
            or claims.get("upn")
        )
        if not email:
            raise AzureAuthError("Missing email in token")

        name = claims.get("name") or email.split("@")[0]

        return AzureUserInfo(
            oid=oid,
            email=email,
            name=name,
            tenant_id=claims.get("tid", ""),
            preferred_username=claims.get("preferred_username"),
            given_name=claims.get("given_name"),
            family_name=claims.get("family_name"),
        )

    async def _find_or_create_user(
        self, user_info: AzureUserInfo
    ) -> tuple[User, Tenant]:
        """
        Find existing user by Azure AD OID or create new user.

        For new users:
        - If their Azure AD tenant matches an existing Dewey tenant, add them to it
        - Otherwise, create a new Dewey tenant for them

        Returns:
            Tuple of (user, tenant)
        """
        # First, try to find user by Azure AD OID
        result = await self.db.execute(
            select(User).where(User.azure_ad_oid == user_info.oid)
        )
        existing_user = result.scalars().first()

        if existing_user:
            # User exists, get their tenant
            result = await self.db.execute(
                select(Tenant).where(Tenant.id == existing_user.tenant_id)
            )
            tenant = result.scalars().first()
            if not tenant:
                raise AzureAuthError("User's tenant not found")

            # Update user info if needed
            if existing_user.email != user_info.email or existing_user.name != user_info.name:
                existing_user.email = user_info.email
                existing_user.name = user_info.name
                await self.db.commit()

            return existing_user, tenant

        # User doesn't exist, check if email is already registered (password user)
        result = await self.db.execute(
            select(User).where(User.email == user_info.email)
        )
        email_user = result.scalars().first()

        if email_user:
            # Link Azure AD to existing password account
            email_user.azure_ad_oid = user_info.oid
            await self.db.commit()

            result = await self.db.execute(
                select(Tenant).where(Tenant.id == email_user.tenant_id)
            )
            tenant = result.scalars().first()
            if not tenant:
                raise AzureAuthError("User's tenant not found")

            return email_user, tenant

        # New user - check if their Azure AD tenant has a matching Dewey tenant
        result = await self.db.execute(
            select(Tenant).where(Tenant.azure_tenant_id == user_info.tenant_id)
        )
        existing_tenant = result.scalars().first()

        if existing_tenant:
            # Add user to existing tenant
            user = await self._create_user_in_tenant(user_info, existing_tenant)
            return user, existing_tenant

        # Create new tenant for this user
        tenant = await self._create_tenant_for_user(user_info)
        user = await self._create_user_in_tenant(user_info, tenant, is_owner=True)

        return user, tenant

    async def _create_tenant_for_user(self, user_info: AzureUserInfo) -> Tenant:
        """Create a new tenant for an Azure AD user."""
        # Generate slug from email domain or name
        email_domain = user_info.email.split("@")[1].split(".")[0]
        base_slug = email_domain.lower().replace("_", "-")

        # Ensure unique slug
        slug = base_slug
        counter = 1
        while True:
            result = await self.db.execute(
                select(Tenant).where(Tenant.slug == slug)
            )
            if not result.scalars().first():
                break
            slug = f"{base_slug}-{counter}"
            counter += 1

        tenant = Tenant(
            name=f"{email_domain.title()} Organization",
            slug=slug,
            subscription_tier="free",
            azure_tenant_id=user_info.tenant_id,
        )
        self.db.add(tenant)
        await self.db.flush()

        # Create default roles
        for role_name, role_data in DEFAULT_ROLES.items():
            role = Role(
                tenant_id=tenant.id,
                name=role_name,
                description=role_data["description"],
                permissions=role_data["permissions"],
                is_system=True,
            )
            self.db.add(role)

        await self.db.flush()
        return tenant

    async def _create_user_in_tenant(
        self, user_info: AzureUserInfo, tenant: Tenant, is_owner: bool = False
    ) -> User:
        """Create a new user in an existing tenant."""
        user = User(
            tenant_id=tenant.id,
            email=user_info.email,
            name=user_info.name,
            azure_ad_oid=user_info.oid,
            is_active=True,
            password_hash=None,  # No password for SSO users
        )
        self.db.add(user)
        await self.db.flush()

        # Assign role
        role_name = "owner" if is_owner else "agent"  # Default role for SSO users
        result = await self.db.execute(
            select(Role).where(Role.tenant_id == tenant.id, Role.name == role_name)
        )
        role = result.scalars().first()

        if role:
            user_role = UserRole(user_id=user.id, role_id=role.id)
            self.db.add(user_role)

        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def link_azure_account(
        self, user: User, code: str
    ) -> User:
        """
        Link an Azure AD account to an existing user.

        Args:
            user: Existing user to link
            code: Authorization code from Azure AD

        Returns:
            Updated user with Azure AD linked
        """
        # Exchange code for tokens
        scopes = ["openid", "profile", "email", "User.Read"]

        result = self.msal_app.acquire_token_by_authorization_code(
            code=code,
            scopes=scopes,
            redirect_uri=self.settings.azure_redirect_uri,
        )

        if "error" in result:
            raise AzureAuthError(
                f"Failed to acquire token: {result.get('error_description', result.get('error'))}"
            )

        id_token_claims = result.get("id_token_claims", {})
        user_info = self._extract_user_info(id_token_claims)

        # Check if this Azure account is already linked to another user
        result = await self.db.execute(
            select(User).where(User.azure_ad_oid == user_info.oid)
        )
        existing = result.scalars().first()

        if existing and existing.id != user.id:
            raise AzureAuthError("This Azure account is already linked to another user")

        # Link the account
        user.azure_ad_oid = user_info.oid
        await self.db.commit()
        await self.db.refresh(user)

        return user
