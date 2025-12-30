# Python Architecture Overview
**Last Updated:** 2025-12-30

## Summary
This project now uses a Python-first architecture:
- **FastAPI** for intake (text + file uploads)
- **Worker scripts** for scraping and scheduled jobs
- **Supabase** for storage
- **AI APIs** for extraction/judging/generation (planned)

---

## Components

### 1) Intake API
**Entry points**
- `POST /intake/text` — JSON `{title, text}`
- `POST /intake/file` — multipart form `title` + `file`

**Code**
- `app/main.py`
- `app/ingest.py`

---

### 2) Scraper Worker
**Purpose**: Fetch category pages and insert into `articles`.

**Code**
- `app/scrape.py`
- `app/worker.py`

**Run**
```bash
python -m app.worker scrape
python -m app.worker extract-links
python -m app.worker scrape-articles
python -m app.worker scrape-loop --interval 3600
python -m app.worker extract
python -m app.worker judge
python -m app.worker generate
python -m app.worker second-judge
```

---

### 3) AI Workers (Planned)
**Purpose**: Summarize, score, generate content.

**Planned modules**
- `app/ai/extract.py`
- `app/ai/judge.py`
- `app/ai/generate.py`

---

## Local Run
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

---

## Deployment (VPS)
1. `git clone` repo
2. `python -m venv .venv && source .venv/bin/activate`
3. `pip install -r requirements.txt`
4. Set env vars: `SUPABASE_URL`, `SUPABASE_KEY`, `OPENAI_API_KEY`
5. Run API as a service (systemd) and worker via cron or service loop

---

## Environment Variables
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `OPENAI_API_KEY` (for AI workers)
- `MANUAL_INTAKE_SCRIPT` (defaults to `scripts/extract_text.py`)
- `MANUAL_INTAKE_DIR` (optional temp dir override)
- `MAX_WORDS` (default 2500)
- `REQUEST_TIMEOUT` (default 30)
