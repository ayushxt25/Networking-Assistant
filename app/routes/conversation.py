"""
Conversation Router
---------------------
Wires the service modules together through FastAPI's APIRouter. This is the
integration point between the HTTP interface and the business logic --
handling request deserialization, service orchestration, and response
serialization.

All routes in this file require authentication (via get_current_user) and
are scoped to the requesting user's own data. /generate-conversation and
/fact-check are additionally rate-limited, since they're the most
expensive (transformer inference) or externally-dependent (Wikipedia call)
operations in the app.

IMPORTANT: every route below takes a `request: Request` parameter, even
where it's otherwise unused. slowapi's @limiter.limit() decorator works by
inspecting the decorated function's signature for a parameter literally
named `request` of type `Request` -- it cannot find the request object any
other way (e.g. via a differently-named parameter). For consistency (and to
avoid this exact bug if a limit is added to a route later) every handler
here follows the same shape: `request: Request` first, then `body:
<PydanticModel>` for the JSON payload.

Endpoints:
  - POST /analyze-event          -> standalone theme extraction
  - POST /fact-check             -> wraps the Wikipedia fact-check service (rate-limited)
  - POST /generate-conversation  -> full pipeline: analyze -> generate -> log -> return (rate-limited)
  - POST /feedback               -> records a like/dislike on a suggestion
  - GET  /history                -> the current user's recent conversation history
  - GET  /feedback-history       -> the current user's recent feedback entries
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.db_models import User
from app.dependencies import get_current_user
from app.models import (
    ConversationRequest,
    ConversationResponse,
    EventAnalysisRequest,
    EventAnalysisResponse,
    FactCheckRequest,
    FactCheckResponse,
    FeedbackHistoryResponse,
    FeedbackRequest,
    FeedbackSummaryResponse,
    HistoryEntryResponse,
)
from app.rate_limit import limiter
from app.services.audit_logger import log_audit_event
from app.services.event_analyzer import extract_event_themes
from app.services.fact_checker import fact_check
from app.services.feedback_logger import load_feedback, log_feedback, summarize_feedback
from app.services.history_logger import load_history, log_conversation
from app.services.context_service import assemble_generation_context
from app.services.topic_generator import finalize_topic_suggestions, generate_topics

router = APIRouter()


@router.post("/analyze-event", response_model=EventAnalysisResponse)
def analyze_event(
    request: Request,
    body: EventAnalysisRequest,
    current_user: User = Depends(get_current_user),
) -> EventAnalysisResponse:
    themes = extract_event_themes(body.description, body.candidate_labels)
    return EventAnalysisResponse(themes=themes)


@router.post("/fact-check", response_model=FactCheckResponse)
@limiter.limit("20/minute")
def check_fact(
    request: Request,
    body: FactCheckRequest,
    current_user: User = Depends(get_current_user),
) -> FactCheckResponse:
    summary = fact_check(body.query)
    return FactCheckResponse(query=body.query, summary=summary)


@router.post("/generate-conversation", response_model=ConversationResponse)
@limiter.limit("10/minute")
def generate_conversation(
    request: Request,
    body: ConversationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationResponse:
    themes = extract_event_themes(body.description)
    generation_context = assemble_generation_context(
        db=db,
        user_id=current_user.id,
        description=body.description,
        interests=body.interests,
        themes=themes,
    )
    try:
        suggestions = generate_topics(
            themes,
            body.interests,
            relationship_context=generation_context.combined_summary,
        )
        suggestions = finalize_topic_suggestions(
            suggestions,
            themes,
            body.interests,
            relationship_context=generation_context.combined_summary,
        )
    except Exception as exc:
        log_audit_event(
            event_type="generation_request",
            status="failed",
            user_id=current_user.id,
            entity_type="conversation",
            message="Conversation generation failed",
            metadata={"error": str(exc)},
            db=db,
        )
        raise HTTPException(
            status_code=503,
            detail="Conversation generation is temporarily unavailable",
        ) from exc

    # Automatic side-effect logging: every successful generation is saved
    # to this user's history without the frontend needing a separate call.
    log_conversation(
        db,
        user_id=current_user.id,
        description=body.description,
        interests=body.interests,
        themes=themes,
        suggestions=suggestions,
    )
    log_audit_event(
        event_type="generation_request",
        status="completed",
        user_id=current_user.id,
        entity_type="conversation",
        message="Conversation generation completed",
        metadata={"theme_count": len(themes), "suggestion_count": len(suggestions)},
        db=db,
    )

    return ConversationResponse(themes=themes, suggestions=suggestions)


@router.post("/feedback")
def submit_feedback(
    request: Request,
    body: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        log_feedback(
            db,
            user_id=current_user.id,
            suggestion=body.suggestion,
            action=body.action,
            category=body.category,
            target_type=body.target_type,
            target_id=body.target_id,
            notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"status": "ok"}


@router.get("/history", response_model=List[HistoryEntryResponse])
def get_history(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[HistoryEntryResponse]:
    entries = load_history(db, user_id=current_user.id, limit=5)
    return [
        HistoryEntryResponse(
            id=e.id,
            description=e.description,
            interests=[i.strip() for i in e.interests.split(",") if i.strip()],
            themes=[t.strip() for t in e.themes.split(",") if t.strip()],
            suggestions=e.suggestions.split("\n") if e.suggestions else [],
            created_at=e.created_at.isoformat(),
        )
        for e in entries
    ]


@router.get("/feedback-history", response_model=List[FeedbackHistoryResponse])
def get_feedback_history(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[FeedbackHistoryResponse]:
    entries = load_feedback(db, user_id=current_user.id, limit=10)
    return [
        FeedbackHistoryResponse(
            suggestion=e.suggestion,
            action=e.action,
            category=e.category,
            target_type=e.target_type,
            target_id=e.target_id,
            notes=e.notes,
            created_at=e.created_at.isoformat(),
        )
        for e in entries
    ]


@router.get("/feedback/summary", response_model=FeedbackSummaryResponse)
def get_feedback_summary(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FeedbackSummaryResponse:
    summary = summarize_feedback(db, user_id=current_user.id)
    return FeedbackSummaryResponse(
        generation_quality=summary.generation_quality.__dict__,
        recommendation_quality=summary.recommendation_quality.__dict__,
        user_preferences=summary.user_preferences.__dict__,
    )
