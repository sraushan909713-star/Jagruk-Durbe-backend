"""add deactivation audit fields to users

Revision ID: a7c19f4e2b03
Revises: 92983b1d461d
Create Date: 2026-06-04 06:30:00.000000

Adds two nullable audit columns to the users table:
  - deactivated_by — id of the admin who suspended this user (FK to users.id)
  - deactivated_at — timestamp of suspension

Populated by the new POST /auth/users/{user_id}/deactivate endpoint and
cleared by POST /auth/users/{user_id}/reactivate. NOT touched by the
existing /delete-account self-deletion flow, which keeps using deleted_at.

A user is "suspended" if  is_active=False AND deleted_at IS NULL.
A user is "deleted"   if  is_active=False AND deleted_at IS NOT NULL.
Reactivation only applies to suspended users.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7c19f4e2b03'
down_revision: Union[str, Sequence[str], None] = '92983b1d461d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — add deactivation audit columns to users."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('deactivated_by', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('deactivated_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema — drop deactivation audit columns from users."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('deactivated_at')
        batch_op.drop_column('deactivated_by')
