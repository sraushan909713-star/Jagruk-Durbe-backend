"""add promises and promise_witnesses tables

Revision ID: c4668229277a
Revises: ee37fb0e523c
Create Date: 2026-05-29 01:04:45.888785

NOTE (Task 4 closure): These two tables physically exist in the dev DB
because the now-removed Base.metadata.create_all() built them silently.
This migration formalizes their creation in Alembic history so that
fresh production deploys will create them via `alembic upgrade head`.

In the dev DB the tables already exist, so on dev we mark this revision
as applied via `alembic stamp head` instead of running `alembic upgrade head`.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4668229277a'
down_revision: Union[str, Sequence[str], None] = 'ee37fb0e523c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — create promises and promise_witnesses tables."""
    op.create_table(
        'promises',
        sa.Column('id', sa.VARCHAR(), nullable=False),
        sa.Column('leader_name', sa.VARCHAR(), nullable=False),
        sa.Column('leader_role', sa.VARCHAR(), nullable=False),
        sa.Column('promise_text', sa.TEXT(), nullable=False),
        sa.Column('made_where', sa.VARCHAR(), nullable=False),
        sa.Column('made_where_detail', sa.VARCHAR(), nullable=True),
        sa.Column('made_on', sa.DATE(), nullable=False),
        sa.Column('deadline', sa.DATE(), nullable=True),
        sa.Column('crowd_count', sa.INTEGER(), nullable=True),
        sa.Column('status', sa.VARCHAR(), nullable=False),
        sa.Column('created_by', sa.VARCHAR(), nullable=False),
        sa.Column('village_id', sa.INTEGER(), nullable=True),
        sa.Column('is_active', sa.BOOLEAN(), nullable=False),
        sa.Column('created_at', sa.DateTime(),
                server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'promise_witnesses',
        sa.Column('id', sa.VARCHAR(), nullable=False),
        sa.Column('promise_id', sa.VARCHAR(), nullable=False),
        sa.Column('user_id', sa.VARCHAR(), nullable=False),
        sa.Column('witnessed_at', sa.DateTime(),
                server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['promise_id'], ['promises.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('promise_id', 'user_id',
                            name=op.f('uq_one_witness_per_promise')),
    )


def downgrade() -> None:
    """Downgrade schema — drop promise tables (witnesses first due to FK)."""
    op.drop_table('promise_witnesses')
    op.drop_table('promises')