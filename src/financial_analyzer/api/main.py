"""Main FastAPI application entrypoint for Financial News Analyzer."""
from __future__ import annotations

from fastapi import FastAPI

from src.financial_analyzer.api.endpoints.analysis import router as analysis_router
from src.financial_analyzer.config.settings import settings

app = FastAPI(title=settings.PROJECT_NAME)
app.include_router(analysis_router)


@app.get("/")
async def root() -> dict[str, str]:
    """Basic health check."""
    return {"status": "ok"}

