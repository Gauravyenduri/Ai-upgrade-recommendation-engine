import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.schemas import (
    Recommendation,
    RecommendationRequest,
    ReviewDecision,
)
from app import repository
from app.services import recommender

router = APIRouter(prefix="/api/v1", tags=["recommendations"])


@router.post("/recommendations", response_model=Recommendation)
def create_recommendation(
    request: RecommendationRequest,
    persist: bool = True,
    db: Session = Depends(get_db),
) -> Recommendation:
    rec = recommender.recommend(db, request)
    if persist:
        repository.save_recommendation(db, rec)
    return rec


@router.get("/recommendations/reviews/pending")
def pending_reviews(db: Session = Depends(get_db)) -> list[dict]:
    rows = repository.list_pending_reviews(db)
    return [
        {
            "id": r.id,
            "resource_id": r.resource_id,
            "strategy": r.recommended_strategy,
            "risk_score": r.risk_score,
            "factors": json.loads(r.factors),
            "review_status": r.review_status,
        }
        for r in rows
    ]


@router.post("/recommendations/{rec_id}/review")
def review(
    rec_id: str,
    decision: ReviewDecision,
    db: Session = Depends(get_db),
) -> dict:
    row = repository.apply_review(db, rec_id, decision)
    if row is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return {
        "id": row.id,
        "review_status": row.review_status,
        "reviewer": row.reviewer,
        "note": row.review_note,
    }
