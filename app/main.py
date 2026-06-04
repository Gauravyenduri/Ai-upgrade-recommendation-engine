"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import routes_health, routes_recommendations
from app.config import get_settings
from app.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="AI-Powered Upgrade Recommendation Engine",
        version="1.0.0",
        description=(
            "Analyzes usage patterns, resource metadata, and operational metrics to "
            "recommend maintenance windows and upgrade strategies — with explainable "
            "output and human-review controls."
        ),
        lifespan=lifespan,
    )
    app.include_router(routes_health.router)
    app.include_router(routes_recommendations.router)
    return app


app = create_app()
