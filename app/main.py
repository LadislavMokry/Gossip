import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel

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


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


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
