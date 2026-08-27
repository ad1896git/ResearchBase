"""Minimal FastAPI adapter smoke application."""

from fastapi import FastAPI

from researchbase import __version__

app = FastAPI(title="ResearchBase", version=__version__)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
