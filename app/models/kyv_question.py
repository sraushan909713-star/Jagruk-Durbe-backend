# app/models/kyv_question.py
# ─────────────────────────────────────────────────────────────
# Know Your Village — Quiz & Poll engine
#
# Three models:
#   KyvQuestion → one question (quiz OR poll), admin posts
#   KyvOption   → an answer choice belonging to a question (2–4 each)
#   KyvAnswer   → one user's answer to one question
#
# Rules:
#   - Only admin/super_admin can create/delete questions
#   - One question is_active at a time (the live one on home);
#     posting a new one closes the previous (handled in router)
#   - Any logged-in user can answer; ONE answer per user per
#     question (DB UniqueConstraint + router check)
#   - "What the village chose" %, history counts, and the
#     answered-count are all DERIVED from KyvAnswer — no extra tables
#
# Type field:
#   "quiz" → has a correct option, reveal shows right/wrong
#   "poll" → opinion, no correct option (all is_correct=False)
# ─────────────────────────────────────────────────────────────

import uuid
from sqlalchemy import (
    Column, String, Text, Integer,
    Boolean, DateTime, ForeignKey, UniqueConstraint
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


# ─── KyvQuestion ─────────────────────────────────────────────

class KyvQuestion(Base):
    __tablename__ = "kyv_questions"

    # ── Identity ──────────────────────────────────────────────
    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # ── Question content ──────────────────────────────────────
    question_text    = Column(Text,   nullable=False)  # Hindi (primary)
    question_text_en = Column(String, nullable=True)   # optional English

    # "quiz" (has correct answer) or "poll" (opinion, no correct answer)
    type = Column(String, nullable=False, default="quiz")

    # Civic / unity payload shown on the reveal screen.
    # Polls may leave this null.
    explanation = Column(Text, nullable=True)

    # ── Audit ─────────────────────────────────────────────────
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    village_id = Column(Integer, nullable=True, default=1)

    # ── Visibility ────────────────────────────────────────────
    # is_active=True  → this is the live question (one at a time)
    # is_active=False → closed / moved to history (also soft-delete)
    is_active = Column(Boolean, default=True, nullable=False)

    # ── Timestamps ────────────────────────────────────────────
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # ── Relationships ─────────────────────────────────────────
    options = relationship(
        "KyvOption",
        back_populates="question",
        order_by="KyvOption.display_order"
    )
    answers = relationship("KyvAnswer", back_populates="question")
    creator = relationship("User", backref="kyv_questions_created", foreign_keys=[created_by])


# ─── KyvOption ───────────────────────────────────────────────

class KyvOption(Base):
    __tablename__ = "kyv_options"

    # ── Identity ──────────────────────────────────────────────
    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # ── Foreign key ───────────────────────────────────────────
    question_id = Column(String, ForeignKey("kyv_questions.id"), nullable=False)

    # ── Option content ────────────────────────────────────────
    option_text   = Column(String,  nullable=False)
    # For quizzes: marks the right answer. For polls: always False.
    is_correct    = Column(Boolean, default=False, nullable=False)
    # Order in which options are shown (admin sets it)
    display_order = Column(Integer, default=0, nullable=False)

    # ── Relationships ─────────────────────────────────────────
    question = relationship("KyvQuestion", back_populates="options")
    answers  = relationship("KyvAnswer", back_populates="option")


# ─── KyvAnswer ───────────────────────────────────────────────

class KyvAnswer(Base):
    __tablename__ = "kyv_answers"

    # ── Identity ──────────────────────────────────────────────
    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # ── Foreign keys ──────────────────────────────────────────
    question_id = Column(String, ForeignKey("kyv_questions.id"), nullable=False)
    option_id   = Column(String, ForeignKey("kyv_options.id"),   nullable=False)
    user_id     = Column(String, ForeignKey("users.id"),         nullable=False)

    # Snapshot of correctness at answer time (so it's stable even
    # if an option is later edited). Polls: always False.
    is_correct = Column(Boolean, default=False, nullable=False)

    # ── Timestamps ────────────────────────────────────────────
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ── Relationships ─────────────────────────────────────────
    question = relationship("KyvQuestion", back_populates="answers")
    option   = relationship("KyvOption", back_populates="answers")
    user     = relationship("User", backref="kyv_answers")

    # ── One answer per user per question ──────────────────────
    __table_args__ = (
        UniqueConstraint("question_id", "user_id",
                         name="uq_one_answer_per_question"),
    )