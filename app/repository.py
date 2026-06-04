"""Persistence helpers for recommendations + their review lifecycle."""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.db_models import StoredRecommendation
from app.models.schemas import Recommendation, ReviewDecision


def save_recommendation(db: Session, rec: Recommendation) -> StoredRecommendation:
    row = StoredRecommendation(
        resource_id=rec.resource_id,
        recommended_strategy=rec.recommended_strategy.value,
        risk_score=rec.risk_score,
        requires_human_review=rec.requires_human_review,
        review_status=rec.review_status,
        explanation=rec.explanation,
        factors=json.dumps(rec.factors),
        generated_at=rec.generated_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_recommendation(db: Session, rec_id: str) -> StoredRecommendation | None:
    return db.get(StoredRecommendation, rec_id)


def list_pending_reviews(db: Session) -> list[StoredRecommendation]:
    return (
        db.query(StoredRecommendation)
        .filter(StoredRecommendation.review_status == "PENDING")
        .order_by(StoredRecommendation.risk_score.desc())
        .all()
    )


def apply_review(db: Session, rec_id: str, decision: ReviewDecision) -> StoredRecommendation | None:
    row = db.get(StoredRecommendation, rec_id)
    if row is None:
        return None
    row.review_status = "APPROVED" if decision.approved else "REJECTED"
    row.reviewer = decision.reviewer
    row.review_note = decision.note
    db.commit()
    db.refresh(row)
    return row
