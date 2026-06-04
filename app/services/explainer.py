"""Builds an explainable recommendation narrative.

Always produces a deterministic, rule-derived explanation; optionally enriches
it with an LLM narrative when one is available and requested.
"""
from __future__ import annotations

from app.models.schemas import (
    MaintenanceWindowSuggestion,
    ResourceMetrics,
    RolloutStrategy,
)
from app.services import llm
from app.services.retrieval import RetrievedOutcome


def _deterministic(metrics: ResourceMetrics, strategy: RolloutStrategy, risk: float,
                   window: MaintenanceWindowSuggestion, factors: list[str]) -> str:
    lines = [
        f"Recommended strategy: {strategy.value} (risk score {risk:.2f}).",
        f"Suggested window: {window.start_hour_utc:02d}:00-{window.end_hour_utc:02d}:00 UTC. "
        f"{window.rationale}",
        "Contributing factors:",
    ]
    lines += [f"  - {f}" for f in factors] or ["  - No elevated risk factors detected."]
    lines.append(
        f"Plan: upgrade {metrics.resource_id} from {metrics.current_version} "
        f"to {metrics.target_version} using a {strategy.value.lower()} rollout."
    )
    return "\n".join(lines)


def build_explanation(*, metrics: ResourceMetrics, strategy: RolloutStrategy, risk: float,
                      window: MaintenanceWindowSuggestion, factors: list[str],
                      retrieved: list[RetrievedOutcome], verbose: bool) -> str:
    base = _deterministic(metrics, strategy, risk, window, factors)

    # Only spend an LLM call when it adds value (verbose, or genuinely risky).
    if not (verbose or risk >= 0.4) or not llm.is_available():
        return base

    hist = "; ".join(
        f"{r.outcome.from_version}->{r.outcome.to_version} "
        f"({'ok' if r.outcome.succeeded else 'failed'}, sim={r.similarity})"
        for r in retrieved[:3]
    ) or "no comparable history"

    prompt = (
        f"Resource {metrics.resource_id} ({metrics.resource_type}, "
        f"criticality {metrics.criticality.value}).\n"
        f"Deterministic analysis:\n{base}\n"
        f"Comparable historical upgrades: {hist}.\n"
        "Write a short paragraph an on-call engineer can act on."
    )
    narrative = llm.generate_narrative(prompt)
    if narrative:
        return base + "\n\nNarrative:\n" + narrative.strip()
    return base
