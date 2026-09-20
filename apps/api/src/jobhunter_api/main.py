from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Request, Response
from pydantic import BaseModel

from jobhunter_api.ai_matching import router as ai_matching_router
from jobhunter_api.ai_routes import router as ai_router
from jobhunter_api.applications import router as applications_router
from jobhunter_api.auth import router as session_router
from jobhunter_api.clarifications import router as clarifications_router
from jobhunter_api.cv_import import router as cv_router
from jobhunter_api.database import check_database
from jobhunter_api.errors import install_errors
from jobhunter_api.hybrid_dedup import router as duplicates_router
from jobhunter_api.job_parser import router as parser_router
from jobhunter_api.job_url import router as job_url_router
from jobhunter_api.jobs import router as jobs_router
from jobhunter_api.matching import router as matching_router
from jobhunter_api.middleware import RequestBoundary
from jobhunter_api.packages import router as packages_router
from jobhunter_api.privacy import router as privacy_router
from jobhunter_api.profile import router as profile_router
from jobhunter_api.research import router as research_router
from jobhunter_api.semantic import router as semantic_router
from jobhunter_api.settings import Settings


class LiveStatus(BaseModel):
    status: Literal["ok"] = "ok"
    service: Literal["jobhunter-api"] = "jobhunter-api"


class DatabaseStatus(BaseModel):
    database: Literal["ok", "unavailable"]


class ReadyStatus(BaseModel):
    status: Literal["ready", "not_ready"]
    checks: DatabaseStatus


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def database_is_ready(settings: Annotated[Settings, Depends(get_settings)]) -> bool:
    return check_database(settings)


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        application.state.settings = (settings if settings is not None else Settings()).runtime()
        yield

    application = FastAPI(
        title="JobHunter AI API",
        version="1.0.0",
        description="Reviewed evidence, deterministic matching and manual application tracking.",
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    install_errors(application)
    application.add_middleware(RequestBoundary)
    application.include_router(session_router)
    application.include_router(profile_router)
    application.include_router(cv_router)
    application.include_router(jobs_router)
    application.include_router(job_url_router)
    application.include_router(matching_router)
    application.include_router(applications_router)
    application.include_router(privacy_router)
    application.include_router(parser_router)
    application.include_router(ai_router)
    application.include_router(semantic_router)
    application.include_router(duplicates_router)
    application.include_router(ai_matching_router)
    application.include_router(packages_router)
    application.include_router(clarifications_router)
    application.include_router(research_router)

    @application.get("/api/health/live", tags=["health"])
    def live() -> LiveStatus:
        return LiveStatus()

    @application.get(
        "/api/health/ready",
        tags=["health"],
        responses={503: {"model": ReadyStatus, "description": "Database unavailable"}},
    )
    def ready(
        response: Response, database_ready: Annotated[bool, Depends(database_is_ready)]
    ) -> ReadyStatus:
        response.headers["Cache-Control"] = "no-store"
        if not database_ready:
            response.status_code = 503
            return ReadyStatus(status="not_ready", checks=DatabaseStatus(database="unavailable"))
        return ReadyStatus(status="ready", checks=DatabaseStatus(database="ok"))

    return application


app = create_app()
