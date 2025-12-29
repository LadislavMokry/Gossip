# Manual Intake Workflow (Text + PDF/DOCX)

## Purpose
Provide a simple intake path for manual text and ebook uploads when scraping is disabled. This workflow inserts items directly into the `articles` table so the rest of the pipeline can run unchanged.

## What It Accepts
- **Pasted text** (JSON body)
- **File uploads**: `.pdf`, `.docx`, `.txt`

Large documents are split by **chapter headings** (Chapter/Kapitola/Part/Book). If no headings are found, the text is chunked into ~2500-word parts.

## Dependencies (Local Dev)
Install these once on the n8n host:

```bash
python -m pip install pdfplumber python-docx
```

For hosted n8n, install the same deps in the container/VM where n8n runs.

## Workflow Summary
- **Webhook** receives JSON or multipart form-data.
- **File branch** writes upload to `/tmp/manual-intake`, runs `scripts/extract_text.py`, then emits one item per chapter.
- **Text branch** splits pasted text by headings.
- Each item is inserted into Supabase `articles` with `source_website = "manual"`.

## Request Format
### Pasted Text (JSON)
```bash
curl -X POST http://localhost:5678/webhook/manual-intake \
  -H "Content-Type: application/json" \
  -d '{"title":"My Book","text":"Chapter 1\n..."}'
```

### File Upload (Multipart)
```bash
curl -X POST http://localhost:5678/webhook/manual-intake \
  -F "title=My Book" \
  -F "file=@/path/to/book.pdf"
```

### Browser Upload (Optional)
Open `assets/manual-intake.html`, set the webhook URL, and submit a file or pasted text.

## Output Behavior
- Each chapter (or chunk) becomes its own row in `articles`.
- `raw_html` contains the extracted plain text.
- `source_url` is auto-generated as `manual:<slug>:<execution-id>:<index>`.

## Notes
- Text-based PDFs work best. Scanned PDFs require OCR (not included).
- If you need different split rules, edit `scripts/extract_text.py`.
