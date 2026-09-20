"""FastAPI app: routes, static files, index page. No runner logic here."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import router

ROOT = Path(__file__).parent.parent
STATIC = ROOT / "static"  # js/css assets
WEB = ROOT / "web"  # html pages

app = FastAPI(title="Readlang Stats")
app.include_router(router)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB / "index.html")
