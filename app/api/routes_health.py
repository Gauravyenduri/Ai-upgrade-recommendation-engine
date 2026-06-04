from fastapi import APIRouter

from app.config import get_settings
from app.services import llm

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    s = get_settings()
    return {
        "status": "ok",
        "app": s.app_name,
        "environment": s.environment,
        "llm_available": llm.is_available(),
    }
