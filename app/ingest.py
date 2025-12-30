import json
import os
import re
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .config import get_settings
from .db import get_supabase


_chapter_re = re.compile(r"^(chapter|kapitola|book|part)\s+([0-9ivxlcdm]+)(\b.*)?$", re.I)


def _slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9-_]+", "-", value).strip("-_")
    value = re.sub(r"-{2,}", "-", value)
    return value.lower() or "upload"


def split_text_into_sections(text: str, title: str, max_words: int) -> list[dict]:
    raw_text = (text or "").strip()
    if not raw_text:
        raise ValueError("No text provided in request body")

    doc_title = (title or "Manual Input").strip()
    lines = [line.strip() for line in raw_text.splitlines()]

    sections: list[dict] = []
    current_title = doc_title
    current_lines: list[str] = []
    saw_heading = False

    def flush(section_title: str) -> None:
        body = "\n".join([l for l in current_lines if l]).strip()
        if body:
            sections.append({"title": section_title, "text": body})
        current_lines.clear()

    for line in lines:
        if not line:
            continue
        if _chapter_re.match(line):
            if current_lines:
                flush(current_title if saw_heading else "Intro")
            current_title = line
            saw_heading = True
            continue
        current_lines.append(line)

    if current_lines:
        flush(current_title)

    if not sections:
        words = [w for w in raw_text.split() if w]
        for i in range(0, len(words), max_words):
            chunk = " ".join(words[i : i + max_words])
            sections.append({"title": f"Part {len(sections) + 1}", "text": chunk})

    return sections


def save_upload_to_temp(filename: str) -> Path:
    settings = get_settings()
    base_dir = settings.manual_intake_dir or os.environ.get("TEMP") or os.environ.get("TMP")
    if not base_dir:
        base_dir = tempfile.gettempdir()
    target_dir = Path(base_dir) / "manual-intake"
    target_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(filename).suffix.lower() or ".bin"
    safe_base = _slugify(Path(filename).stem)
    target_name = f"{safe_base}-{uuid.uuid4().hex}{ext}"
    return target_dir / target_name


def run_extractor(file_path: Path, title: str, max_words: int) -> dict:
    settings = get_settings()
    script_path = settings.manual_intake_script
    cmd = [
        os.environ.get("PYTHON", os.environ.get("PYTHON_EXECUTABLE", sys.executable)),
        script_path,
        "--input",
        str(file_path),
        "--title",
        title or "Manual Upload",
        "--max-words",
        str(max_words),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "extract_text.py failed")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("extract_text.py returned invalid JSON") from exc


def build_rows(sections: list[dict], title: str, source_website: str, request_id: str) -> list[dict]:
    rows = []
    safe_title = _slugify(title or "upload")
    for idx, section in enumerate(sections):
        rows.append(
            {
                "source_url": f"{source_website}:{safe_title}:{request_id}:{idx}",
                "source_website": source_website,
                "title": section.get("title") or title or "Manual Input",
                "raw_html": section.get("text") or "",
                "content": section.get("text") or "",
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    return rows


def insert_articles(rows: list[dict]) -> list[dict]:
    if not rows:
        return []
    supabase = get_supabase()
    response = supabase.table("articles").insert(rows).execute()
    return response.data or []
