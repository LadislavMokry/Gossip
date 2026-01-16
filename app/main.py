import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .admin import (
    create_project,
    create_source,
    delete_source,
    get_source,
    get_youtube_account,
    list_projects,
    list_source_items,
    list_sources,
    scrape_project,
    scrape_source,
    update_project,
    update_source,
    upsert_youtube_account,
)
from .config import get_settings
from .ingest import (
    build_rows,
    insert_articles,
    run_extractor,
    save_upload_to_temp,
    split_text_into_sections,
)


app = FastAPI(title="Gossip Intake API", version="0.1.0")


class TextIntake(BaseModel):
    title: str | None = None
    text: str


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class SourceCreate(BaseModel):
    name: str
    source_type: str
    url: str
    enabled: bool = True
    config: dict | None = None


class SourceUpdate(BaseModel):
    name: str | None = None
    source_type: str | None = None
    url: str | None = None
    enabled: bool | None = None
    config: dict | None = None


class YoutubeAccountUpdate(BaseModel):
    refresh_token: str
    channel_title: str | None = None
    scopes: list[str] | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def admin_ui() -> HTMLResponse:
    root = Path(__file__).resolve().parent.parent
    html_path = root / "assets" / "admin.html"
    if not html_path.exists():
        return HTMLResponse("<h1>Admin UI missing</h1>", status_code=500)
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.post("/intake/text")
def intake_text(payload: TextIntake) -> dict:
    settings = get_settings()
    request_id = uuid.uuid4().hex
    sections = split_text_into_sections(payload.text, payload.title or "Manual Input", settings.max_words)
    rows = build_rows(sections, payload.title or "Manual Input", "manual", request_id)
    inserted = insert_articles(rows)
    return {"status": "ok", "inserted": len(inserted), "ids": [r["id"] for r in inserted]}


@app.post("/intake/file")
def intake_file(title: str | None = None, file: UploadFile = File(...)) -> dict:
    settings = get_settings()
    request_id = uuid.uuid4().hex
    target_path = save_upload_to_temp(file.filename or "upload.bin")
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with target_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    payload = run_extractor(target_path, title or "Manual Upload", settings.max_words)
    if payload.get("error"):
        raise RuntimeError(payload["error"])

    sections = payload.get("sections", [])
    rows = build_rows(sections, payload.get("document_title") or title or "Manual Upload", "manual", request_id)
    inserted = insert_articles(rows)
    return {"status": "ok", "inserted": len(inserted), "ids": [r["id"] for r in inserted]}


@app.get("/api/projects")
def api_list_projects() -> list[dict]:
    return list_projects()


@app.post("/api/projects")
def api_create_project(payload: ProjectCreate) -> dict:
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="name is required")
    return create_project(payload.name, payload.description)


@app.patch("/api/projects/{project_id}")
def api_update_project(project_id: str, payload: ProjectUpdate) -> dict:
    return update_project(project_id, payload.model_dump())


@app.get("/api/projects/{project_id}/sources")
def api_list_sources(project_id: str) -> list[dict]:
    return list_sources(project_id)


@app.post("/api/projects/{project_id}/sources")
def api_create_source(project_id: str, payload: SourceCreate) -> dict:
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="name is required")
    if not payload.url.strip():
        raise HTTPException(status_code=400, detail="url is required")
    return create_source(project_id, payload.model_dump())


@app.patch("/api/sources/{source_id}")
def api_update_source(source_id: str, payload: SourceUpdate) -> dict:
    return update_source(source_id, payload.model_dump())


@app.delete("/api/sources/{source_id}")
def api_delete_source(source_id: str) -> dict:
    delete_source(source_id)
    return {"status": "ok"}


@app.post("/api/projects/{project_id}/scrape")
def api_scrape_project(project_id: str, max_items: int = Query(10, ge=1, le=50)) -> dict:
    results = scrape_project(project_id, max_items=max_items)
    return {"status": "ok", "results": [r.__dict__ for r in results]}


@app.post("/api/sources/{source_id}/scrape")
def api_scrape_source(source_id: str, max_items: int = Query(10, ge=1, le=50)) -> dict:
    source = get_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="source not found")
    result = scrape_source(source, max_items=max_items)
    return {"status": "ok", "result": result.__dict__}


@app.get("/api/sources/{source_id}/items")
def api_list_source_items(source_id: str, limit: int = Query(10, ge=1, le=50)) -> list[dict]:
    return list_source_items(source_id, limit=limit)


@app.get("/api/projects/{project_id}/youtube")
def api_get_youtube_account(project_id: str) -> dict | None:
    return get_youtube_account(project_id)


@app.post("/api/projects/{project_id}/youtube")
def api_upsert_youtube_account(project_id: str, payload: YoutubeAccountUpdate) -> dict:
    if not payload.refresh_token.strip():
        raise HTTPException(status_code=400, detail="refresh_token is required")
    return upsert_youtube_account(project_id, payload.refresh_token, payload.channel_title, payload.scopes)
