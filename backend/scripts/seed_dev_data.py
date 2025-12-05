#!/usr/bin/env python3
"""
Development seed script for Dewey.

Creates a test tenant with users and roles for development and testing.
This script is idempotent - running it multiple times will not create duplicates.

Usage:
    cd backend
    python -m scripts.seed_dev_data
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import User, Role, UserRole, DEFAULT_ROLES


# Development seed data
DEV_TENANT = {
    "name": "Demo Organization",
    "slug": "demo",
    "subscription_tier": "pro",
}

DEV_USERS = [
    {
        "email": "owner@deweydemo.com",
        "name": "Demo Owner",
        "password": "demo1234",
        "role": "owner",
    },
    {
        "email": "admin@deweydemo.com",
        "name": "Demo Admin",
        "password": "demo1234",
        "role": "admin",
    },
    {
        "email": "manager@deweydemo.com",
        "name": "Demo Manager",
        "password": "demo1234",
        "role": "manager",
    },
    {
        "email": "agent@deweydemo.com",
        "name": "Demo Agent",
        "password": "demo1234",
        "role": "agent",
    },
    {
        "email": "viewer@deweydemo.com",
        "name": "Demo Viewer",
        "password": "demo1234",
        "role": "viewer",
    },
]


async def seed_database():
    """Seed the database with development data."""
    settings = get_settings()

    engine = create_async_engine(settings.async_database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Check if demo tenant already exists
        result = await session.execute(
            select(Tenant).where(Tenant.slug == DEV_TENANT["slug"])
        )
        existing_tenant = result.scalars().first()

        if existing_tenant:
            print(f"Demo tenant '{DEV_TENANT['slug']}' already exists (id: {existing_tenant.id})")
            tenant = existing_tenant
        else:
            # Create tenant
            tenant = Tenant(**DEV_TENANT)
            session.add(tenant)
            await session.flush()
            print(f"Created tenant: {tenant.name} (id: {tenant.id})")

        # Check/create roles
        roles_created = {}
        for role_name, role_data in DEFAULT_ROLES.items():
            result = await session.execute(
                select(Role).where(
                    Role.tenant_id == tenant.id,
                    Role.name == role_name,
                )
            )
            existing_role = result.scalars().first()

            if existing_role:
                print(f"  Role '{role_name}' already exists")
                roles_created[role_name] = existing_role
            else:
                role = Role(
                    tenant_id=tenant.id,
                    name=role_name,
                    description=role_data["description"],
                    permissions=role_data["permissions"],
                    is_system=True,
                )
                session.add(role)
                roles_created[role_name] = role
                print(f"  Created role: {role_name} ({len(role_data['permissions'])} permissions)")

        await session.flush()

        # Check/create users
        for user_data in DEV_USERS:
            result = await session.execute(
                select(User).where(
                    User.tenant_id == tenant.id,
                    User.email == user_data["email"],
                )
            )
            existing_user = result.scalars().first()

            if existing_user:
                print(f"  User '{user_data['email']}' already exists")
                continue

            user = User(
                tenant_id=tenant.id,
                email=user_data["email"],
                name=user_data["name"],
                password_hash=hash_password(user_data["password"]),
                is_active=True,
            )
            session.add(user)
            await session.flush()

            # Assign role
            role = roles_created.get(user_data["role"])
            if role:
                user_role = UserRole(user_id=user.id, role_id=role.id)
                session.add(user_role)
                print(f"  Created user: {user_data['email']} (role: {user_data['role']})")

        await session.commit()

        print("\nSeed data complete!")
        print("\nTest accounts (all passwords: demo1234):")
        for user_data in DEV_USERS:
            print(f"  - {user_data['email']} ({user_data['role']})")


async def main():
    """Main entry point."""
    print("Seeding development database...\n")
    await seed_database()


if __name__ == "__main__":
    asyncio.run(main())
