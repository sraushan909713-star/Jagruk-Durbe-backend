# app/schemas/kyv.py
# ─────────────────────────────────────────────────────────────
# Pydantic schemas for Know Your Village (quiz + poll) feature.
# ─────────────────────────────────────────────────────────────

from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime


# ─── Option Schemas ──────────────────────────────────────────

class OptionCreate(BaseModel):
    """One answer choice, supplied by admin when creating a question."""
    option_text:   str
    is_correct:    bool = False        # quizzes mark one True; polls all False
    display_order: int  = 0


class OptionPublic(BaseModel):
    """An option as shown to users BEFORE they answer — no is_correct leak."""
    id:            str
    option_text:   str
    display_order: int

    class Config:
        from_attributes = True


class OptionResult(BaseModel):
    """An option WITH results — shown after answering / in history."""
    id:            str
    option_text:   str
    display_order: int
    is_correct:    bool          # safe to reveal post-answer
    vote_count:    int  = 0      # computed
    percentage:    float = 0.0   # computed (0–100)

    class Config:
        from_attributes = True


# ─── Question Schemas ────────────────────────────────────────

class QuestionCreate(BaseModel):
    """Admin creates a question with its options."""
    question_text:    str
    question_text_en: Optional[str] = None
    type:             str                       # "quiz" or "poll"
    explanation:      Optional[str] = None
    options:          List[OptionCreate]

    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        allowed = {"quiz", "poll"}
        if v.lower() not in allowed:
            raise ValueError(f"type must be one of: {allowed}")
        return v.lower()

    @field_validator("options")
    @classmethod
    def validate_options(cls, v):
        if len(v) < 2 or len(v) > 4:
            raise ValueError("A question must have between 2 and 4 options.")
        return v


class AnswerSubmit(BaseModel):
    """User submits their chosen option."""
    option_id: str


# ─── Question Responses ──────────────────────────────────────

class ActiveQuestionResponse(BaseModel):
    """The live question. If the user has already answered, results are
    included and has_answered=True; otherwise options hide is_correct."""
    id:               str
    question_text:    str
    question_text_en: Optional[str] = None
    type:             str
    explanation:      Optional[str] = None      # only sent after answering
    total_answers:    int  = 0                  # computed
    has_answered:     bool = False              # for the logged-in user
    my_option_id:     Optional[str] = None      # what they picked, if answered
    options_public:   Optional[List[OptionPublic]] = None   # before answering
    options_result:   Optional[List[OptionResult]] = None   # after answering
    created_at:       datetime

    class Config:
        from_attributes = True


class HistoryQuestionResponse(BaseModel):
    """A past question with full results — for the History tab."""
    id:               str
    question_text:    str
    question_text_en: Optional[str] = None
    type:             str
    explanation:      Optional[str] = None
    total_answers:    int = 0
    options_result:   List[OptionResult]
    created_at:       datetime

    class Config:
        from_attributes = True


class AnswerResult(BaseModel):
    """Returned immediately after a user answers — drives the reveal screen."""
    correct:        bool                 # was the user right (always False for polls)
    correct_option_id: Optional[str] = None   # null for polls
    explanation:    Optional[str] = None
    total_answers:  int
    options_result: List[OptionResult]
    my_answered_count: int               # updated user stat
    my_points:         int               # updated user stat


# ─── User Stats (Profile) ────────────────────────────────────

class KyvMeResponse(BaseModel):
    """The logged-in user's Know Your Village stats — for Profile."""
    answered_count: int
    points:         int

    class Config:
        from_attributes = True

# ─── Village Facts Schemas ───────────────────────────────────

class VillageCreate(BaseModel):
    """super_admin adds a panchayat village."""
    name:            str
    is_home_village: bool = False
    display_order:   int  = 0


class VillagePublic(BaseModel):
    id:              str
    name:            str
    is_home_village: bool
    display_order:   int

    class Config:
        from_attributes = True


class MetricCreate(BaseModel):
    """super_admin defines a metric (a dropdown category)."""
    name:          str
    unit:          Optional[str] = None
    display_order: int  = 0
    is_active:     bool = True


class MetricPublic(BaseModel):
    id:            str
    name:          str
    unit:          Optional[str] = None
    display_order: int
    is_active:     bool

    class Config:
        from_attributes = True


class VillageValueUpsert(BaseModel):
    """super_admin sets the number for one (village × metric) cell."""
    village_id: str
    metric_id:  str
    value:      Optional[int] = None
    source:     Optional[str] = None
    as_of_date: Optional[str] = None


class VillageValuePublic(BaseModel):
    village_id: str
    metric_id:  str
    value:      Optional[int] = None
    source:     Optional[str] = None
    as_of_date: Optional[str] = None

    class Config:
        from_attributes = True


class VillageFactsResponse(BaseModel):
    """One combined payload for the Village Facts tab — load once,
    switch metrics client-side (instant, no extra calls)."""
    villages: List[VillagePublic]
    metrics:  List[MetricPublic]
    values:   List[VillageValuePublic]