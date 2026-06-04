"""Core decision engine.

Turns operational signals into an explainable upgrade recommendation:
a rollout strategy, a risk score, a suggested low-traffic maintenance window,
and a human-review gate. Every branch contributes a human-readable *factor*
so the recommendation is fully auditable.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.schemas import (
    Criticality,
    MaintenanceWindowSuggestion,
    Recommendation,
    RecommendationRequest,
    ResourceMetrics,
    RolloutStrategy,
)
from app.services import retrieval
from app.services.explainer import build_explanation


def _suggest_window(metrics: ResourceMetrics) -> MaintenanceWindowSuggestion:
    """Pick the 2-hour window with the lowest mean utilization."""
    if not metrics.hourly_usage:
        return MaintenanceWindowSuggestion(
            start_hour_utc=2, end_hour_utc=4,
            rationale="No usage data; defaulting to typical low-traffic window 02:00-04:00 UTC.",
        )
    usage = {u.hour: u.utilization for u in metrics.hourly_usage}
    best_hour, best_load = 0, float("inf")
    for h in range(24):
        load = usage.get(h, 0) + usage.get((h + 1) % 24, 0)
        if load < best_load:
            best_load, best_hour = load, h
    return MaintenanceWindowSuggestion(
        start_hour_utc=best_hour,
        end_hour_utc=(best_hour + 2) % 24,
        rationale=f"Lowest observed two-hour utilization (~{best_load/2:.0f}% avg) "
                  f"starts at {best_hour:02d}:00 UTC.",
    )


def _risk_score(metrics: ResourceMetrics, hist_failure_rate: float) -> tuple[float, list[str]]:
    """Blend operational signals + historical evidence into a 0-1 risk score."""
    factors: list[str] = []
    score = 0.0

    score += 0.30 * metrics.error_rate
    if metrics.error_rate > 0.05:
        factors.append(f"Elevated recent error rate ({metrics.error_rate:.1%}).")

    score += 0.20 * (metrics.cpu_p95 / 100.0)
    if metrics.cpu_p95 > 80:
        factors.append(f"High CPU p95 ({metrics.cpu_p95:.0f}%).")

    if metrics.open_incidents > 0:
        score += min(0.20, 0.05 * metrics.open_incidents)
        factors.append(f"{metrics.open_incidents} open incident(s) on the resource.")

    crit_weight = {Criticality.LOW: 0.0, Criticality.MEDIUM: 0.1, Criticality.HIGH: 0.25}
    score += crit_weight[metrics.criticality]
    if metrics.criticality == Criticality.HIGH:
        factors.append("Resource is business-critical (HIGH criticality).")

    score += 0.25 * hist_failure_rate
    if hist_failure_rate > 0.2:
        factors.append(f"Similar past upgrades failed at {hist_failure_rate:.0%}.")

    if metrics.days_since_last_upgrade > 365:
        score += 0.05
        factors.append("Large version drift (>1 year since last upgrade).")

    return min(1.0, round(score, 3)), factors


def _strategy_for(risk: float, metrics: ResourceMetrics) -> RolloutStrategy:
    if metrics.criticality == Criticality.HIGH or risk >= 0.5:
        return RolloutStrategy.CANARY
    if risk >= 0.2:
        return RolloutStrategy.LINEAR
    return RolloutStrategy.ALL_AT_ONCE


def recommend(db: Session, request: RecommendationRequest) -> Recommendation:
    settings = get_settings()
    metrics = request.metrics

    retrieved = retrieval.retrieve_similar(db, metrics)
    hist_failure_rate = retrieval.historical_failure_rate(retrieved)

    risk, factors = _risk_score(metrics, hist_failure_rate)
    strategy = _strategy_for(risk, metrics)
    window = _suggest_window(metrics)

    requires_review = risk >= settings.human_review_risk_threshold or (
        settings.high_criticality_requires_review
        and metrics.criticality == Criticality.HIGH
    )
    if requires_review:
        factors.append(
            f"Flagged for human review (risk {risk:.2f} ≥ "
            f"{settings.human_review_risk_threshold} or HIGH criticality)."
        )

    explanation = build_explanation(
        metrics=metrics, strategy=strategy, risk=risk,
        window=window, factors=factors, retrieved=retrieved,
        verbose=request.explain_verbose,
    )

    return Recommendation(
        resource_id=metrics.resource_id,
        recommended_strategy=strategy,
        risk_score=risk,
        maintenance_window=window,
        requires_human_review=requires_review,
        factors=factors,
        explanation=explanation,
        generated_at=dt.datetime.now(dt.timezone.utc),
        review_status="PENDING" if requires_review else "AUTO_APPROVED",
    )
