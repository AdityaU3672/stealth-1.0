from __future__ import annotations

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.routes import (
    auth_router,
    chat_router,
    connectors_router,
    dashboard_router,
    events_router,
    feature_requests_router,
    ingest_router,
    jobs_router,
    signals_router,
    synthesis_router,
    triggers_router,
)
from src.services.triggers import trigger_service

structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)

app = FastAPI(title="Ingestion & Synthesis Microservice", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(dashboard_router)
app.include_router(signals_router)
app.include_router(feature_requests_router)
app.include_router(connectors_router)
app.include_router(ingest_router)
app.include_router(synthesis_router)
app.include_router(events_router)
app.include_router(jobs_router)
app.include_router(triggers_router)


@app.on_event("startup")
async def start_trigger_runtime() -> None:
    if settings.TRIGGER_RUNTIME_ENABLED:
        trigger_service.start_runtime()


@app.on_event("shutdown")
async def stop_trigger_runtime() -> None:
    if settings.TRIGGER_RUNTIME_ENABLED:
        await trigger_service.stop_runtime()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
