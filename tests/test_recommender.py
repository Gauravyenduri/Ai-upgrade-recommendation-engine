import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.db_models import Base, UpgradeOutcome
from app.models.schemas import (
    Criticality,
    HourlyUsage,
    RecommendationRequest,
    ResourceMetrics,
    RolloutStrategy,
)
from app.services import recommender


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    s.add(UpgradeOutcome(resource_type="database", from_version="14.2", to_version="15.4",
                         strategy="ALL_AT_ONCE", criticality="HIGH", succeeded=False,
                         rollback_required=True))
    s.commit()
    yield s
    s.close()


def _metrics(**kw) -> ResourceMetrics:
    base = dict(resource_id="db-1", resource_type="database", current_version="14.2",
                target_version="15.4", criticality=Criticality.MEDIUM)
    base.update(kw)
    return ResourceMetrics(**base)


def test_low_risk_resource_gets_all_at_once(db):
    # resource_type "cache" has no failure history in the corpus -> genuinely low risk
    req = RecommendationRequest(metrics=_metrics(resource_type="cache", error_rate=0.0,
                                                 cpu_p95=10, criticality=Criticality.LOW))
    rec = recommender.recommend(db, req)
    assert rec.recommended_strategy == RolloutStrategy.ALL_AT_ONCE
    assert rec.requires_human_review is False


def test_high_criticality_forces_canary_and_review(db):
    req = RecommendationRequest(metrics=_metrics(criticality=Criticality.HIGH))
    rec = recommender.recommend(db, req)
    assert rec.recommended_strategy == RolloutStrategy.CANARY
    assert rec.requires_human_review is True


def test_window_picks_lowest_traffic(db):
    usage = [HourlyUsage(hour=h, utilization=90) for h in range(24)]
    usage[3] = HourlyUsage(hour=3, utilization=5)
    usage[4] = HourlyUsage(hour=4, utilization=5)
    req = RecommendationRequest(metrics=_metrics(hourly_usage=usage))
    rec = recommender.recommend(db, req)
    assert rec.maintenance_window.start_hour_utc == 3


def test_high_error_rate_raises_risk(db):
    low = recommender.recommend(db, RecommendationRequest(metrics=_metrics(error_rate=0.0)))
    high = recommender.recommend(db, RecommendationRequest(metrics=_metrics(error_rate=0.4)))
    assert high.risk_score > low.risk_score
