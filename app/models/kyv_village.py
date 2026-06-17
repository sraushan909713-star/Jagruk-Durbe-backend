# app/models/kyv_village.py
# ─────────────────────────────────────────────────────────────
# Know Your Village — Village Facts (demographics)
#
# Three models powering the Village Facts tab:
#   KyvVillage      → a village in the Ghuthiya panchayat
#                     (Durbe flagged is_home_village=True)
#   KyvMetric       → an ADMIN-DEFINABLE category (the dropdown items):
#                     "जनसंख्या", "वोटर", "युवा", "रोज़गार" … super_admin
#                     can add new metrics WITHOUT an app update / migration
#   KyvVillageValue → the number for one (village × metric) pair,
#                     with source + as-of date for credibility
#
# Why three tables (not fixed columns): Raushan wants to add new
# metrics freely later. Flexible metric→value pairs make that a
# data entry, never a schema change.
#
# Rules:
#   - Public read (everyone sees the charts)
#   - super_admin only creates/edits villages, metrics, values
#   - One value per (village, metric) pair (UniqueConstraint)
#   - Charts render only for metrics with is_active=True; empty
#     state shows until data is added (build platform now, fill later)
# ─────────────────────────────────────────────────────────────

import uuid
from sqlalchemy import (
    Column, String, Integer,
    Boolean, DateTime, ForeignKey, UniqueConstraint
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


# ─── KyvVillage ──────────────────────────────────────────────

class KyvVillage(Base):
    __tablename__ = "kyv_villages"

    # ── Identity ──────────────────────────────────────────────
    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # ── Village content ───────────────────────────────────────
    name = Column(String, nullable=False)          # "दुर्बे", "बरांव" …

    # Durbe = True → highlighted green in charts, drives "our village" view
    is_home_village = Column(Boolean, default=False, nullable=False)

    # Order in which villages appear in the comparison bars
    display_order = Column(Integer, default=0, nullable=False)

    # ── Timestamps ────────────────────────────────────────────
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ── Relationships ─────────────────────────────────────────
    values = relationship(
        "KyvVillageValue",
        back_populates="village",
        cascade="all, delete-orphan"
    )


# ─── KyvMetric ───────────────────────────────────────────────

class KyvMetric(Base):
    __tablename__ = "kyv_metrics"

    # ── Identity ──────────────────────────────────────────────
    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # ── Metric content ────────────────────────────────────────
    name = Column(String, nullable=False)           # "जनसंख्या", "वोटर" …
    # Optional display unit, e.g. "people", "%", "घर"
    unit = Column(String, nullable=True)

    # Order in the dropdown
    display_order = Column(Integer, default=0, nullable=False)

    # Hide a metric from the dropdown without deleting its data
    is_active = Column(Boolean, default=True, nullable=False)

    # ── Timestamps ────────────────────────────────────────────
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ── Relationships ─────────────────────────────────────────
    values = relationship(
        "KyvVillageValue",
        back_populates="metric",
        cascade="all, delete-orphan"
    )


# ─── KyvVillageValue ─────────────────────────────────────────

class KyvVillageValue(Base):
    __tablename__ = "kyv_village_values"

    # ── Identity ──────────────────────────────────────────────
    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # ── Foreign keys ──────────────────────────────────────────
    village_id = Column(String, ForeignKey("kyv_villages.id"), nullable=False)
    metric_id  = Column(String, ForeignKey("kyv_metrics.id"),  nullable=False)

    # The number itself. Nullable so a (village, metric) cell can be
    # left blank until the data is collected.
    value = Column(Integer, nullable=True)

    # Credibility line shown under the charts
    source     = Column(String, nullable=True)   # "ECI 2024"
    as_of_date = Column(String, nullable=True)    # "जून 2026" / "2024"

    # ── Timestamps ────────────────────────────────────────────
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())

    # ── Relationships ─────────────────────────────────────────
    village = relationship("KyvVillage", back_populates="values")
    metric  = relationship("KyvMetric",  back_populates="values")

    # ── One value per (village, metric) ───────────────────────
    __table_args__ = (
        UniqueConstraint("village_id", "metric_id",
                         name="uq_one_value_per_village_metric"),
    )