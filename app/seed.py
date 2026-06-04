"""Seed the retrieval corpus with historical upgrade outcomes.

Run:  python -m app.seed
"""
from app.db.session import SessionLocal, init_db
from app.models.db_models import UpgradeOutcome

SEED = [
    dict(resource_type="database", from_version="14.2", to_version="15.4",
         strategy="CANARY", criticality="HIGH", succeeded=True, rollback_required=False,
         notes="clean major upgrade with canary"),
    dict(resource_type="database", from_version="13.8", to_version="15.4",
         strategy="ALL_AT_ONCE", criticality="HIGH", succeeded=False, rollback_required=True,
         notes="big jump, replication lag spike, rolled back"),
    dict(resource_type="database", from_version="15.2", to_version="15.6",
         strategy="LINEAR", criticality="MEDIUM", succeeded=True, rollback_required=False,
         notes="minor upgrade, smooth"),
    dict(resource_type="database", from_version="15.4", to_version="16.1",
         strategy="CANARY", criticality="MEDIUM", succeeded=True, rollback_required=False),
    dict(resource_type="cache", from_version="6.2", to_version="7.0",
         strategy="LINEAR", criticality="LOW", succeeded=True, rollback_required=False),
]


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        if db.query(UpgradeOutcome).count() == 0:
            db.add_all(UpgradeOutcome(**row) for row in SEED)
            db.commit()
            print(f"Seeded {len(SEED)} upgrade outcomes.")
        else:
            print("Corpus already seeded; skipping.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
