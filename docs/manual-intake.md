# Manual Intake Workflow (Text + PDF/DOCX)

## Purpose
Provide the primary intake path for uploaded text and book files or pasted text. The FastAPI intake service inserts items directly into the `articles` table so the rest of the pipeline can run unchanged.

## What It Accepts
- **Pasted text** (JSON body)
- **File uploads**: `.pdf`, `.docx`, `.txt`

Large documents are split by **chapter headings** (Chapter/Kapitola/Part/Book). If no headings are found, the text is chunked into ~2500-word parts.

## Dependencies (Local Dev)
Install these once on the API host:

```bash
python -m pip install pdfplumber python-docx
```

For hosted deployment, install the same deps in the container/VM where the API runs.

## Flow Summary
- **/intake/text** receives JSON text.
- **/intake/file** receives multipart file uploads.
- Files are extracted via `scripts/extract_text.py`, then split into chapters.
- Each item is inserted into Supabase `articles` with `source_website = "manual"`.

## Request Format
### Pasted Text (JSON)
```bash
curl -X POST http://localhost:8000/intake/text \
  -H "Content-Type: application/json" \
  -d '{"title":"My Book","text":"Chapter 1\n..."}'
```

### File Upload (Multipart)
```bash
curl -X POST http://localhost:8000/intake/file \
  -F "title=My Book" \
  -F "file=@/path/to/book.pdf"
```

### Browser Upload (Optional)
Open `assets/manual-intake.html`, set the API URL, and submit a file or pasted text.

## Output Behavior
- Each chapter (or chunk) becomes its own row in `articles`.
- `raw_html` contains the extracted plain text (kept for schema compatibility).
- `source_url` is auto-generated as `manual:<slug>:<execution-id>:<index>`.
- `scraped_at` functions as the ingestion timestamp (manual intake time).

## Notes
- Text-based PDFs work best. Scanned PDFs require OCR (not included).
- If you need different split rules, edit `scripts/extract_text.py`.
