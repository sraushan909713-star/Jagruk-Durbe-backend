"""mandi v2 redesign — items, units, rebuilt vendor_listings

Revision ID: 92983b1d461d
Revises: c4668229277a
Create Date: 2026-05-29

Drops the old vendor_listings (test data only) and rebuilds it
with FKs to two new master tables: items and units.
Also seeds the units table with the common set.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func
import uuid

# revision identifiers, used by Alembic.
revision = "92983b1d461d"
down_revision = "c4668229277a"
branch_labels = None
depends_on = None


def upgrade():
    # ── 1. Drop existing vendor_listings (test data only) ───
    op.drop_table("vendor_listings")

    # ── 2. Create units table ───────────────────────────────
    op.create_table(
        "units",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True, index=True),
        sa.Column("name_hindi", sa.String(), nullable=True),
        sa.Column("is_custom", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_by_vendor_id", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=func.now()),
    )

    # ── 3. Create items table ───────────────────────────────
    op.create_table(
        "items",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, index=True),
        sa.Column("name_hindi", sa.String(), nullable=True),
        sa.Column("default_unit_id", sa.String(), sa.ForeignKey("units.id"), nullable=True),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="999"),
        sa.Column("is_custom", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_by_vendor_id", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=func.now()),
    )

    # ── 4. Recreate vendor_listings with new shape ──────────
    op.create_table(
        "vendor_listings",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("village_id", sa.String(), nullable=False, server_default="true"),
        sa.Column("vendor_id", sa.String(), nullable=False, index=True),
        sa.Column("vendor_name", sa.String(), nullable=False),
        sa.Column("item_id", sa.String(), sa.ForeignKey("items.id"), nullable=False, index=True),
        sa.Column("unit_id", sa.String(), sa.ForeignKey("units.id"), nullable=False),
        sa.Column("mode", sa.Enum("buy", "sell", name="trademode"), nullable=False, index=True),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column(
            "stock_status",
            sa.Enum("in_stock", "limited", "out_of_stock", name="stockstatus"),
            nullable=False,
            server_default="in_stock",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=func.now()),
        sa.UniqueConstraint("vendor_id", "item_id", "mode", name="uq_vendor_item_mode"),
    )

    # ── 5. Seed units inline ────────────────────────────────
    units_table = sa.table(
        "units",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
        sa.column("name_hindi", sa.String),
        sa.column("is_custom", sa.Boolean),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(units_table, [
        {"id": str(uuid.uuid4()), "name": "kg",       "name_hindi": "किलो",     "is_custom": False, "is_active": True},
        {"id": str(uuid.uuid4()), "name": "gram",     "name_hindi": "ग्राम",     "is_custom": False, "is_active": True},
        {"id": str(uuid.uuid4()), "name": "litre",    "name_hindi": "लीटर",     "is_custom": False, "is_active": True},
        {"id": str(uuid.uuid4()), "name": "ml",       "name_hindi": "मिली",     "is_custom": False, "is_active": True},
        {"id": str(uuid.uuid4()), "name": "quintal",  "name_hindi": "क्विंटल",   "is_custom": False, "is_active": True},
        {"id": str(uuid.uuid4()), "name": "dozen",    "name_hindi": "दर्जन",    "is_custom": False, "is_active": True},
        {"id": str(uuid.uuid4()), "name": "piece",    "name_hindi": "नग",       "is_custom": False, "is_active": True},
        {"id": str(uuid.uuid4()), "name": "bori",     "name_hindi": "बोरी",     "is_custom": False, "is_active": True},
    ])


def downgrade():
    op.drop_table("vendor_listings")
    op.drop_table("items")
    op.drop_table("units")

    # Recreate the OLD vendor_listings shape so downgrade is non-destructive
    op.create_table(
        "vendor_listings",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("village_id", sa.String(), nullable=False, server_default="true"),
        sa.Column("vendor_id", sa.String(), nullable=False),
        sa.Column("vendor_name", sa.String(), nullable=False),
        sa.Column("product_name", sa.String(), nullable=False),
        sa.Column("product_name_hindi", sa.String(), nullable=True),
        sa.Column(
            "category",
            sa.Enum("crops", "animal_feed", name="vendorcategory"),
            nullable=False,
        ),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(), nullable=False),
        sa.Column(
            "stock_status",
            sa.Enum("in_stock", "limited", "out_of_stock", name="stockstatus"),
            nullable=False,
            server_default="in_stock",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=func.now()),
    )