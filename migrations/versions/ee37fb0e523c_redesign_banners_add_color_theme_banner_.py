"""redesign banners + add color_theme + banner_contacts

Revision ID: ee37fb0e523c
Revises: 7e09d8eee040
Create Date: 2026-05-15 10:50:20.968321

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ee37fb0e523c'
down_revision: Union[str, Sequence[str], None] = '7e09d8eee040'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ── Modify banners table (batch mode for SQLite portability) ──────────
    with op.batch_alter_table('banners') as batch_op:
        # New NOT NULL columns — server_default backfills the 2 existing
        # test rows. New banners from the API will always provide real
        # values (Pydantic enforces it), so default is just a bootstrap.
        batch_op.add_column(
            sa.Column('color_theme', sa.String(), nullable=False,
                      server_default='indigo_night')
        )
        batch_op.add_column(
            sa.Column('description', sa.Text(), nullable=False,
                      server_default='No description')
        )

        # New optional columns
        batch_op.add_column(sa.Column('event_location', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('event_date',     sa.String(), nullable=True))
        batch_op.add_column(sa.Column('event_time',     sa.String(), nullable=True))
        batch_op.add_column(sa.Column('entry_fee',      sa.String(), nullable=True))
        batch_op.add_column(sa.Column('youtube_link',   sa.String(), nullable=True))
        batch_op.add_column(sa.Column('external_link',  sa.String(), nullable=True))

        # Drop obsolete columns
        batch_op.drop_column('redirect_type')
        batch_op.drop_column('bg_color_end')
        batch_op.drop_column('bg_color_start')
        batch_op.drop_column('redirect_target')

    # ── Create banner_contacts join table (autogenerate missed this) ──────
    op.create_table(
        'banner_contacts',
        sa.Column('id',        sa.String(), nullable=False),
        sa.Column('banner_id', sa.String(), nullable=False),
        sa.Column('user_id',   sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['banner_id'], ['banners.id']),
        sa.ForeignKeyConstraint(['user_id'],   ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('banner_contacts')

    with op.batch_alter_table('banners') as batch_op:
        # Restore old columns
        batch_op.add_column(sa.Column('redirect_target', sa.VARCHAR(), nullable=True))
        batch_op.add_column(sa.Column('bg_color_start',  sa.VARCHAR(), nullable=True))
        batch_op.add_column(sa.Column('bg_color_end',    sa.VARCHAR(), nullable=True))
        batch_op.add_column(sa.Column('redirect_type',   sa.VARCHAR(), nullable=True))

        # Drop new columns
        batch_op.drop_column('external_link')
        batch_op.drop_column('youtube_link')
        batch_op.drop_column('entry_fee')
        batch_op.drop_column('event_time')
        batch_op.drop_column('event_date')
        batch_op.drop_column('event_location')
        batch_op.drop_column('description')
        batch_op.drop_column('color_theme')