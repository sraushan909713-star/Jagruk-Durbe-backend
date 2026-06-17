# app/routers/kyv.py
# ─────────────────────────────────────────────────────────────
# Know Your Village (quiz + poll) API
#
# Endpoint map:
#
#   ANY LOGGED-IN USER (view)
#   GET  /kyv/active            → the live question (results only if you answered)
#   GET  /kyv/history           → past questions with full results
#   GET  /kyv/me                → your answered_count + points (for Profile)
#
#   VERIFIED DURBE NIWASI (+admins) — civic action
#   POST /kyv/{question_id}/answer  → submit your answer, get the reveal
#
#   ADMIN / SUPER ADMIN
#   POST   /kyv                 → create a question (auto-closes previous active)
#   DELETE /kyv/{question_id}   → soft-delete  (ANY admin — Golden Rule)
#
# Notes:
#   - One question is_active at a time. Posting a new one closes the old.
#   - One answer per user per question (DB UniqueConstraint + check).
#   - "What the village chose" %, totals, history = DERIVED from kyv_answers.
#   - quiz → has a correct option, reveal shows right/wrong.
#     poll → opinion, correct always False, no right/wrong.
# ─────────────────────────────────────────────────────────────

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.kyv_question import KyvQuestion, KyvOption, KyvAnswer
from app.models.kyv_village import KyvVillage, KyvMetric, KyvVillageValue
from app.models.user import User
from app.schemas.kyv import (
    QuestionCreate, AnswerSubmit,
    ActiveQuestionResponse, HistoryQuestionResponse,
    OptionPublic, OptionResult, AnswerResult, KyvMeResponse,
    VillageCreate, VillagePublic, MetricCreate, MetricPublic,
    VillageValueUpsert, VillageValuePublic, VillageFactsResponse,
)
from app.core.security import decode_access_token
from app.core.deps import get_current_user, require_admin, require_super_admin, require_verified

router = APIRouter(
    prefix="/kyv",
    tags=["Know Your Village"]
)

POINTS_PER_CORRECT = 10


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _option_results(question: KyvQuestion, db: Session) -> List[OptionResult]:
    """Build per-option vote counts + percentages for a question."""
    total = db.query(KyvAnswer).filter(
        KyvAnswer.question_id == question.id
    ).count()

    results = []
    for opt in question.options:  # already ordered by display_order
        votes = db.query(KyvAnswer).filter(
            KyvAnswer.option_id == opt.id
        ).count()
        pct = round((votes / total) * 100, 1) if total > 0 else 0.0
        results.append(OptionResult(
            id            = opt.id,
            option_text   = opt.option_text,
            display_order = opt.display_order,
            is_correct    = opt.is_correct,
            vote_count    = votes,
            percentage    = pct,
        ))
    return results


def _user_id_from_optional_token(
    credentials: Optional[HTTPAuthorizationCredentials]
) -> Optional[str]:
    """Pull user id from an optional bearer token (for view endpoints)."""
    if not credentials:
        return None
    payload = decode_access_token(credentials.credentials)
    return payload.get("sub") if payload else None


# ─────────────────────────────────────────────────────────────
# VIEW ENDPOINTS (any logged-in user; token optional for results)
# ─────────────────────────────────────────────────────────────

@router.get("/active", response_model=Optional[ActiveQuestionResponse])
def get_active_question(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))
):
    """
    Returns the current live question, or null if none.
    If the caller has already answered, results + explanation are included;
    otherwise options are returned WITHOUT is_correct (no answer leak).
    """
    question = db.query(KyvQuestion).filter(
        KyvQuestion.is_active == True
    ).order_by(KyvQuestion.created_at.desc()).first()

    if not question:
        return None

    user_id = _user_id_from_optional_token(credentials)
    total = db.query(KyvAnswer).filter(
        KyvAnswer.question_id == question.id
    ).count()

    my_answer = None
    if user_id:
        my_answer = db.query(KyvAnswer).filter(
            KyvAnswer.question_id == question.id,
            KyvAnswer.user_id     == user_id
        ).first()

    resp = ActiveQuestionResponse(
        id               = question.id,
        question_text    = question.question_text,
        question_text_en = question.question_text_en,
        type             = question.type,
        total_answers    = total,
        has_answered     = my_answer is not None,
        created_at       = question.created_at,
    )

    if my_answer:
        # Already answered → send results + explanation
        resp.explanation    = question.explanation
        resp.my_option_id   = my_answer.option_id
        resp.options_result = _option_results(question, db)
    else:
        # Not answered → hide is_correct
        resp.options_public = [
            OptionPublic(
                id            = o.id,
                option_text   = o.option_text,
                display_order = o.display_order,
            ) for o in question.options
        ]

    return resp


@router.get("/history", response_model=List[HistoryQuestionResponse])
def get_history(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))
):
    """
    Past questions (closed / no longer active), newest first, with full results.
    Active question is excluded — it lives on /active.
    """
    questions = db.query(KyvQuestion).filter(
        KyvQuestion.is_active == False
    ).order_by(KyvQuestion.created_at.desc()).all()

    out = []
    for q in questions:
        total = db.query(KyvAnswer).filter(KyvAnswer.question_id == q.id).count()
        out.append(HistoryQuestionResponse(
            id               = q.id,
            question_text    = q.question_text,
            question_text_en = q.question_text_en,
            type             = q.type,
            explanation      = q.explanation,
            total_answers    = total,
            options_result   = _option_results(q, db),
            created_at       = q.created_at,
        ))
    return out


@router.get("/me", response_model=KyvMeResponse)
def get_my_stats(
    current_user: User = Depends(get_current_user)
):
    """The logged-in user's KYV stats — for the Profile screen."""
    return KyvMeResponse(
        answered_count = current_user.kyv_answered_count,
        points         = current_user.kyv_points,
    )


# ─────────────────────────────────────────────────────────────
# ANSWER (verified Durbe Niwasi + admins)
# ─────────────────────────────────────────────────────────────

@router.post("/{question_id}/answer", response_model=AnswerResult)
def answer_question(
    question_id: str,
    data: AnswerSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_verified)
):
    """
    Submit an answer to a question. One per user per question.
    Returns the reveal payload: correctness, results, explanation, updated stats.
    """
    question = db.query(KyvQuestion).filter(
        KyvQuestion.id == question_id
    ).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found.")
    if not question.is_active:
        raise HTTPException(status_code=400, detail="This question is closed.")

    # ── Validate the chosen option belongs to THIS question ───
    option = db.query(KyvOption).filter(
        KyvOption.id          == data.option_id,
        KyvOption.question_id == question_id
    ).first()
    if not option:
        raise HTTPException(status_code=400, detail="Invalid option for this question.")

    # ── Already answered? ─────────────────────────────────────
    existing = db.query(KyvAnswer).filter(
        KyvAnswer.question_id == question_id,
        KyvAnswer.user_id     == current_user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You have already answered this question.")

    # ── Correctness: quizzes only; polls always False ─────────
    is_correct = bool(option.is_correct) if question.type == "quiz" else False

    answer = KyvAnswer(
        question_id = question_id,
        option_id   = option.id,
        user_id     = current_user.id,
        is_correct  = is_correct,
    )
    db.add(answer)

    # ── Update user stats (never-resets count; +points on correct) ──
    current_user.kyv_answered_count = (current_user.kyv_answered_count or 0) + 1
    if is_correct:
        current_user.kyv_points = (current_user.kyv_points or 0) + POINTS_PER_CORRECT

    db.commit()

    # ── Build the reveal ──────────────────────────────────────
    correct_option_id = None
    if question.type == "quiz":
        co = next((o for o in question.options if o.is_correct), None)
        correct_option_id = co.id if co else None

    return AnswerResult(
        correct           = is_correct,
        correct_option_id = correct_option_id,
        explanation       = question.explanation,
        total_answers     = db.query(KyvAnswer).filter(KyvAnswer.question_id == question_id).count(),
        options_result    = _option_results(question, db),
        my_answered_count = current_user.kyv_answered_count,
        my_points         = current_user.kyv_points,
    )


# ─────────────────────────────────────────────────────────────
# ADMIN
# ─────────────────────────────────────────────────────────────

@router.post("", response_model=ActiveQuestionResponse, status_code=201)
def create_question(
    data: QuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """
    Admin creates a question + its options.
    Auto-closes any currently active question (one live at a time).
    For polls, any is_correct flags are ignored (forced False).
    """
    # ── Close the existing active question ────────────────────
    db.query(KyvQuestion).filter(
        KyvQuestion.is_active == True
    ).update({KyvQuestion.is_active: False})

    question = KyvQuestion(
        question_text    = data.question_text,
        question_text_en = data.question_text_en,
        type             = data.type,
        explanation      = data.explanation,
        created_by       = current_user.id,
        village_id       = 1,
        is_active        = True,
    )
    db.add(question)
    db.flush()  # get question.id before adding options

    is_quiz = data.type == "quiz"
    for o in data.options:
        db.add(KyvOption(
            question_id   = question.id,
            option_text   = o.option_text,
            is_correct    = bool(o.is_correct) if is_quiz else False,
            display_order = o.display_order,
        ))

    db.commit()
    db.refresh(question)

    # Fresh question → no answers yet, return public options
    return ActiveQuestionResponse(
        id               = question.id,
        question_text    = question.question_text,
        question_text_en = question.question_text_en,
        type             = question.type,
        total_answers    = 0,
        has_answered     = False,
        options_public   = [
            OptionPublic(
                id            = o.id,
                option_text   = o.option_text,
                display_order = o.display_order,
            ) for o in question.options
        ],
        created_at       = question.created_at,
    )


@router.delete("/{question_id}", status_code=200)
def delete_question(
    question_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """
    Soft-delete a question. ANY admin/super_admin can delete ANY question
    (Golden Rule — not gated behind created_by).
    """
    question = db.query(KyvQuestion).filter(
        KyvQuestion.id == question_id
    ).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found.")

    question.is_active = False
    db.commit()
    return {"message": "Question deleted successfully."}

# ─────────────────────────────────────────────────────────────
# VILLAGE FACTS — demographics charts
#
#   PUBLIC (view)
#   GET  /kyv/village-facts        → combined payload (villages,
#                                     metrics, values) — load once,
#                                     switch metric client-side
#
#   SUPER ADMIN (manage)
#   POST   /kyv/villages           → add a village
#   DELETE /kyv/villages/{id}      → remove a village (+ its values)
#   POST   /kyv/metrics            → add a metric (dropdown category)
#   DELETE /kyv/metrics/{id}       → remove a metric (+ its values)
#   PUT    /kyv/village-values     → upsert one (village × metric) value
# ─────────────────────────────────────────────────────────────

@router.get("/village-facts", response_model=VillageFactsResponse)
def get_village_facts(db: Session = Depends(get_db)):
    """
    Everything the Village Facts charts need, in one call.
    Public — anyone can see the village data. Only active metrics
    are returned (so a hidden metric leaves the dropdown).
    """
    villages = db.query(KyvVillage).order_by(
        KyvVillage.display_order, KyvVillage.name
    ).all()
    metrics = db.query(KyvMetric).filter(
        KyvMetric.is_active == True
    ).order_by(KyvMetric.display_order, KyvMetric.name).all()

    # Only values whose metric is active (skip hidden-metric values)
    active_metric_ids = {m.id for m in metrics}
    values = [
        v for v in db.query(KyvVillageValue).all()
        if v.metric_id in active_metric_ids
    ]

    return VillageFactsResponse(
        villages = [VillagePublic.model_validate(v) for v in villages],
        metrics  = [MetricPublic.model_validate(m) for m in metrics],
        values   = [VillageValuePublic.model_validate(v) for v in values],
    )


@router.post("/villages", response_model=VillagePublic, status_code=201)
def create_village(
    data: VillageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Add a panchayat village (super_admin)."""
    village = KyvVillage(
        name            = data.name,
        is_home_village = data.is_home_village,
        display_order   = data.display_order,
    )
    db.add(village)
    db.commit()
    db.refresh(village)
    return village


@router.delete("/villages/{village_id}", status_code=200)
def delete_village(
    village_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Remove a village and its values (cascade) — super_admin."""
    village = db.query(KyvVillage).filter(
        KyvVillage.id == village_id
    ).first()
    if not village:
        raise HTTPException(status_code=404, detail="Village not found.")
    db.delete(village)
    db.commit()
    return {"message": "Village deleted successfully."}


@router.post("/metrics", response_model=MetricPublic, status_code=201)
def create_metric(
    data: MetricCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Add a metric / dropdown category (super_admin)."""
    metric = KyvMetric(
        name          = data.name,
        unit          = data.unit,
        display_order = data.display_order,
        is_active     = data.is_active,
    )
    db.add(metric)
    db.commit()
    db.refresh(metric)
    return metric


@router.delete("/metrics/{metric_id}", status_code=200)
def delete_metric(
    metric_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Remove a metric and its values (cascade) — super_admin."""
    metric = db.query(KyvMetric).filter(
        KyvMetric.id == metric_id
    ).first()
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found.")
    db.delete(metric)
    db.commit()
    return {"message": "Metric deleted successfully."}


@router.put("/village-values", response_model=VillageValuePublic)
def upsert_village_value(
    data: VillageValueUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """
    Set (create or update) the value for one village × metric cell.
    The data-entry grid sends one of these per village for the
    selected metric.  super_admin only.
    """
    # ── Validate the village + metric exist ───────────────────
    village = db.query(KyvVillage).filter(
        KyvVillage.id == data.village_id
    ).first()
    if not village:
        raise HTTPException(status_code=404, detail="Village not found.")
    metric = db.query(KyvMetric).filter(
        KyvMetric.id == data.metric_id
    ).first()
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found.")

    # ── Upsert: update existing cell, else create ─────────────
    cell = db.query(KyvVillageValue).filter(
        KyvVillageValue.village_id == data.village_id,
        KyvVillageValue.metric_id  == data.metric_id
    ).first()

    if cell:
        cell.value      = data.value
        cell.source     = data.source
        cell.as_of_date = data.as_of_date
    else:
        cell = KyvVillageValue(
            village_id = data.village_id,
            metric_id  = data.metric_id,
            value      = data.value,
            source     = data.source,
            as_of_date = data.as_of_date,
        )
        db.add(cell)

    db.commit()
    db.refresh(cell)
    return cell