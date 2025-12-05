"""Make contact email nullable for voter imports.

Revision ID: make_contact_email_nullable
Revises: add_job_arq_fields
Create Date: 2025-12-05 14:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "make_contact_email_nullable"
down_revision: Union[str, None] = "add_job_arq_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the existing unique constraint on (tenant_id, email)
    op.drop_constraint("uq_contact_tenant_email", "contact", type_="unique")

    # Make email column nullable
    op.alter_column(
        "contact",
        "email",
        existing_type=sa.VARCHAR(),
        nullable=True,
    )

    # Create a partial unique index that only applies to non-NULL emails
    # This allows multiple contacts with NULL email while keeping email unique when present
    op.execute(
        """
        CREATE UNIQUE INDEX uq_contact_tenant_email_partial
        ON contact (tenant_id, email)
        WHERE email IS NOT NULL
        """
    )


def downgrade() -> None:
    # Drop the partial unique index
    op.drop_index("uq_contact_tenant_email_partial", table_name="contact")

    # Make email NOT NULL again (this will fail if there are NULL emails)
    op.alter_column(
        "contact",
        "email",
        existing_type=sa.VARCHAR(),
        nullable=False,
    )

    # Recreate the original unique constraint
    op.create_unique_constraint(
        "uq_contact_tenant_email", "contact", ["tenant_id", "email"]
    )
