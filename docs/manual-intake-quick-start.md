# Manual Intake - Quick Start Guide
**Last Updated**: 2025-12-30
**Est. Build Time**: 30-60 minutes
**Difficulty**: Beginner-Intermediate

---

## Overview
This API ingests uploaded PDF/DOCX/TXT files or pasted text and inserts rows into the `articles` table. It is the primary ingestion path for the MVP.

**What it does**:
- Accepts multipart file uploads or JSON text via API
- Extracts text and splits by chapter headings (or chunks if no headings)
- Stores each part as one row in `articles`

**API code**: `app/main.py`
**Full doc**: `docs/manual-intake.md`

---

## Prerequisites
- Supabase credentials set in env (`SUPABASE_URL`, `SUPABASE_KEY`)
- Python deps installed:
```bash
python -m pip install pdfplumber python-docx
```

---

## Step-by-Step

### Step 1: Run API
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Step 3: Test with Pasted Text
```bash
curl -X POST http://localhost:8000/intake/text \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"Sample Text\",\"text\":\"Chapter 1\\nThis is a test.\"}"
```

### Step 4: Test with File Upload
```bash
curl -X POST http://localhost:8000/intake/file \
  -F "title=Sample Book" \
  -F "file=@/path/to/book.pdf"
```

### Step 5: Verify in Supabase
```sql
SELECT id, source_url, source_website, scraped_at
FROM articles
ORDER BY scraped_at DESC
LIMIT 10;
```

Expected:
- `source_website = 'manual'`
- `raw_html` contains extracted plain text

---

## Success Criteria
- Upload or paste creates rows in `articles`
- Each chapter or chunk becomes a separate row
- Downstream extraction and judging workflows can run unchanged

---

## Next Steps
1. Build AI worker: extraction + judging
2. Add scraping worker schedule (cron)
