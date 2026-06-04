AI-Powered Upgrade Recommendation Engine
A FastAPI service that decides when and how to upgrade a resource. It analyzes usage patterns, resource metadata, and operational metrics, retrieves the outcomes of similar past upgrades, and produces an explainable recommendation: a suggested maintenance window, a rollout strategy, a risk score, and a plain-language rationale. High-risk recommendations are routed into a human-review queue rather than auto-approved.

Built with Python 3.12, FastAPI, SQLAlchemy 2.0, and Pydantic v2, with optional OpenAI enrichment that degrades gracefully to fully deterministic output when no key is set.

What it does
Given metrics for a resource, the engine:

Suggests a maintenance window — picks the two-hour slot with the lowest mean utilization from the supplied hourly usage profile (falling back to a typical low-traffic window when no data is available).
Scores risk (0–1) — blends recent error rate, p95 CPU pressure, open incidents, criticality, time since the last upgrade (version drift), and the historical failure rate of similar past upgrades retrieved from a stored corpus. Each contributing factor is captured as a human-readable reason.
Chooses a rollout strategy — CANARY, LINEAR, or ALL_AT_ONCE, scaled to the risk and the resource's criticality.
Explains itself — always produces a deterministic explanation; an LLM narrative is layered on only when it adds value (a verbose request, or a genuinely risky recommendation) and a key is configured. If the LLM call fails, it silently falls back to the deterministic text.
Gates human review — a recommendation is marked PENDING review when its risk exceeds the configured threshold (default 0.6) or it targets a high-criticality resource; otherwise it is AUTO_APPROVED.
Why retrieval, not a black box
The risk score is explainable by construction. Rather than a single opaque number, it is a sum of named factors, and the historical component comes from a transparent retrieval step (retrieve_similar) that ranks past UpgradeOutcome records by resource-type match and version proximity. You can always see which prior upgrades informed a recommendation and how much each factor moved the score — which is what makes the output safe to act on and to review.

API
Base path /api/v1. Interactive docs at /docs.

Method	Path	Purpose
POST	/api/v1/recommendations	Generate a recommendation for a resource
GET	/api/v1/recommendations/reviews/pending	List recommendations awaiting human review
POST	/api/v1/recommendations/{rec_id}/review	Approve or reject a pending recommendation
GET	/health	Liveness/health check
A recommendation response includes the suggested window, rollout strategy, risk score, the list of risk factors, the explanation, and the review status. See requests-demo.http for ready-to-run examples.

Configuration
All settings are environment variables (see .env.example):

Variable	Default	Meaning
DATABASE_URL	sqlite:///./recommendations.db	SQLAlchemy connection string (swap for Postgres in production)
OPENAI_API_KEY	unset	Optional; absence disables LLM narrative (deterministic fallback)
OPENAI_MODEL	gpt-4o-mini	Model used for narrative enrichment
LLM_ENABLED	true	Master switch for LLM enrichment
HUMAN_REVIEW_RISK_THRESHOLD	0.6	Risk at or above which review is required
HIGH_CRITICALITY_REQUIRES_REVIEW	true	Force review for high-criticality resources
Running locally
pip install -r requirements.txt -r requirements-dev.txt

# load the historical upgrade-outcome corpus used by retrieval
python -m app.seed

# run the API
uvicorn app.main:app --reload
# docs: http://localhost:8000/docs
With Docker
docker compose up --build
Tests
pytest
The suite covers the core recommendation logic — window selection, risk scoring with and without historical failures, strategy selection, and the human-review gating — plus the API surface end-to-end with an in-memory database.

Project layout
app/
  config.py                 # env-driven settings
  main.py                   # FastAPI app + lifespan init
  db/session.py             # engine, session, init_db
  models/
    schemas.py              # Pydantic request/response models + enums
    db_models.py            # StoredRecommendation, UpgradeOutcome (corpus)
  services/
    recommender.py          # window, risk score, strategy, recommend()
    retrieval.py            # retrieve_similar + historical_failure_rate
    explainer.py            # deterministic explanation + optional LLM enrichment
    llm.py                  # lazy OpenAI client with graceful fallback
  repository.py             # persistence + review workflow
  api/
    routes_recommendations.py
    routes_health.py
  seed.py                   # historical UpgradeOutcomes for retrieval
tests/                      # pytest suite
Tech stack
Python 3.12 · FastAPI · SQLAlchemy 2.0 · Pydantic v2 / pydantic-settings · OpenAI (optional) · pytest · Docker · GitHub Actions.
