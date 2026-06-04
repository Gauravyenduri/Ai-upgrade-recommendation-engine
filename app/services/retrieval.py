"""Retrieval pipeline.

Finds historically-similar upgrade outcomes to ground a recommendation
(a lightweight RAG-style retrieval over the UpgradeOutcome corpus). Similarity
is a transparent, explainable score over resource_type / criticality / version
proximity rather than an opaque embedding — which matters for an auditable
operational system.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.db_models import UpgradeOutcome
from app.models.schemas import ResourceMetrics


@dataclass
class RetrievedOutcome:
    outcome: UpgradeOutcome
    similarity: float


def _version_proximity(a: str, b: str) -> float:
    """1.0 for identical major version, decaying for larger gaps."""
    try:
        amaj = int(a.split(".")[0])
        bmaj = int(b.split(".")[0])
    except (ValueError, IndexError):
        return 0.5
    gap = abs(amaj - bmaj)
    return max(0.0, 1.0 - gap * 0.25)


def retrieve_similar(db: Session, metrics: ResourceMetrics, k: int = 5) -> list[RetrievedOutcome]:
    candidates = (
        db.query(UpgradeOutcome)
        .filter(UpgradeOutcome.resource_type == metrics.resource_type)
        .all()
    )
    scored: list[RetrievedOutcome] = []
    for c in candidates:
        sim = 0.0
        sim += 0.4 if c.criticality == metrics.criticality.value else 0.0
        sim += 0.3 * _version_proximity(c.to_version, metrics.target_version)
        sim += 0.3 * _version_proximity(c.from_version, metrics.current_version)
        scored.append(RetrievedOutcome(outcome=c, similarity=round(sim, 3)))
    scored.sort(key=lambda r: r.similarity, reverse=True)
    return scored[:k]


def historical_failure_rate(retrieved: list[RetrievedOutcome]) -> float:
    """Weighted failure rate among retrieved outcomes (0-1)."""
    if not retrieved:
        return 0.0
    total_w = sum(r.similarity for r in retrieved) or 1.0
    failures = sum(r.similarity for r in retrieved if not r.outcome.succeeded)
    return round(failures / total_w, 3)
