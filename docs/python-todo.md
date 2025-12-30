# Python Content Automation - Task List (Deep)
Last Updated: 2025-12-30
Target: Python (FastAPI + worker scripts)

---

Legend
- [ ] Not Started
- [->] In Progress
- [x] Completed
- [!] Blocked

---

Phase 0: Environment + Database
- [ ] Create .venv
- [ ] Install requirements.txt
- [ ] Set env vars: SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY
- [ ] Optional env vars: MANUAL_INTAKE_SCRIPT, MANUAL_INTAKE_DIR, MAX_WORDS
- [ ] Run db/supabase-schema.sql in Supabase SQL Editor
- [ ] Verify tables exist: articles, posts, performance_metrics, model_performance
- [ ] Verify indexes exist (articles processed/scored/source_url)
- [ ] Verify unique constraint on articles.source_url
- [ ] Add .env to gitignore (if not already)

Phase 1: Intake API (FastAPI)
- [ ] Start API: uvicorn app.main:app --reload --port 8000
- [ ] GET /health returns {"status":"ok"}

Text Intake
- [ ] POST /intake/text accepts JSON {title, text}
- [ ] Validate required fields (text not empty)
- [ ] Split by headings (Chapter/Kapitola/Part/Book)
- [ ] Fallback chunking by MAX_WORDS
- [ ] Insert rows into articles with source_website = "manual"
- [ ] Populate source_url with stable manual:<slug>:<request_id>:<index>
- [ ] Populate raw_html and content with extracted text
- [ ] Confirm scraped_at is set

File Intake
- [ ] POST /intake/file accepts multipart (title, file)
- [ ] Accept PDF, DOCX, TXT
- [ ] Save upload to temp dir (MANUAL_INTAKE_DIR or system temp)
- [ ] Run scripts/extract_text.py
- [ ] Parse JSON output: document_title, sections
- [ ] Insert rows into articles

Testing
- [ ] /intake/text inserts >=1 row
- [ ] /intake/file PDF inserts >=1 row
- [ ] /intake/file DOCX inserts >=1 row
- [ ] /intake/file TXT inserts >=1 row
- [ ] Verify sections split as expected
- [ ] Verify article rows have processed=false, scored=false

Phase 2: Scraper Worker
Sources
- [ ] Confirm initial website source list (category pages)
- [ ] Add sources:
  - https://www.topky.sk/se/15/Prominenti
  - https://www.cas.sk/r/prominenti
  - https://www1.pluska.sk/r/soubiznis
  - https://refresher.sk/osobnosti
  - https://www.startitup.sk/kategoria/kultura/
- [ ] Store source list in app/scrape.py
- [ ] Add per-source overrides if needed (headers, timeouts)

Scraper Execution
- [ ] python -m app.worker scrape runs without crash
- [ ] Category pages inserted into category_pages
- [ ] python -m app.worker extract-links inserts into article_urls
- [ ] python -m app.worker scrape-articles inserts into articles
- [ ] Non-200 response does not stop other sources
- [ ] Deduped by source_url unique constraint
- [ ] Validate new rows in Supabase

Scheduling
- [ ] Manual run for testing (no schedule yet)
- [ ] Later: run scrape-loop with interval 3600
- [ ] Ensure no overlap (single loop process)
- [ ] Confirm scraping hourly on VPS

Phase 3: Extraction Worker (Planned)
- [ ] Add app/ai/extract.py
- [ ] Query articles where processed=false
- [ ] Skip rows without raw_html
- [ ] Call LLM to summarize
- [ ] Store summary, content if extracted, processed=true
- [ ] Add retry on LLM errors (max retries)
- [ ] Add token usage logging (if available)
- [ ] Batch size config

Testing
- [ ] Summaries generated for manual intake rows
- [ ] Summaries generated for scraped rows
- [ ] processed=true after success
- [ ] Failures are marked for retry

Phase 4: First Judge (Planned)
- [ ] Add app/ai/first_judge.py
- [ ] Query articles where scored=false and processed=true
- [ ] Score 1-10
- [ ] Assign format_assignments based on score
- [ ] Store judge_score, format_assignments, scored=true
- [ ] Queue size logic (optional)

Testing
- [ ] Scores stored correctly
- [ ] Format rules applied correctly
- [ ] Low-score items rejected

Phase 5: Generation (Planned)
- [ ] Add app/ai/generate.py
- [ ] Query articles with format_assignments != []
- [ ] Generate all requested formats in one call per model
- [ ] Insert outputs into posts (one row per model)
- [ ] Store generating_model, content_type, content JSON

Testing
- [ ] 3 model outputs per article
- [ ] Content JSON schema valid per format

Phase 6: Second Judge (Planned)
- [ ] Add app/ai/second_judge.py
- [ ] Group posts by article and format
- [ ] Select best version
- [ ] Mark posts.selected=true for winners
- [ ] Update model_performance

Phase 7: Publishing (Planned)
- [ ] Define platforms and credentials
- [ ] Build rate-limited posting worker
- [ ] Store post_url, posted_at
- [ ] Handle API errors and retries

Phase 7B: Video/Audio (Planned)
- [ ] Define 1-2 minute, 9:16 video pipeline (images + TTS + captions)
- [ ] Generate script from summary
- [ ] Scene splitting rules (1 image per 5-10 seconds)
- [ ] Image generation (low-cost) per scene
- [ ] TTS voiceover (OpenAI for testing)
- [ ] Captions via ASR (Whisper or equivalent)
- [ ] FFmpeg assembly (images + audio + captions)
- [ ] Output MP4 1080x1920
- [ ] Add cost check for image generation (10 images @ 9:16)

Phase 8: Monitoring + Ops
- [ ] Structured logging
- [ ] Error alerts (email/Discord)
- [ ] Cost tracking (tokens, API usage)
- [ ] Data retention policy
- [ ] Backups (Supabase)

Quick Test Checklist
- [ ] /health ok
- [ ] /intake/text ok
- [ ] /intake/file ok
- [ ] Scraper inserts rows
- [ ] Duplicate source_url rejected
