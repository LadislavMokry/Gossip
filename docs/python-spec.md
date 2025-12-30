# Python Content Automation Spec (Deep)
Last Updated: 2025-12-30
Target Platform: Python (FastAPI + worker scripts)
Storage: Supabase
Scope: Manual intake + scraping -> AI pipeline -> publishing

---

1. Overview

1.1 Goal
Build a Python-first system that ingests text (upload/paste) and scraped pages, then runs extraction, judging, and content generation for multi-format outputs. The MVP is topic-agnostic.

1.2 High-Level Flow
Manual Intake (upload/paste) -> articles
Scraping (category pages) -> articles
Extraction (summary) -> articles
First Judge (score + formats) -> articles
Generation (multi-format) -> posts
Second Judge (select best) -> posts
Publishing -> posts
Performance Tracking -> performance_metrics / model_performance

1.3 Design Principles
- Modular: each stage is an independent worker
- Idempotent: safe to re-run jobs
- Cost-aware: batching, prompt caching
- Observable: logs + minimal metrics

---

2. Architecture

2.1 Services
- API: FastAPI for manual intake
- Workers: cron or loop processes for scraping and AI pipeline
- Storage: Supabase Postgres + Storage (optional)

2.2 Code Layout
- app/main.py (API)
- app/ingest.py (split + extract helpers)
- app/scrape.py (scraper)
- app/worker.py (runner)
- app/ai/* (planned)

2.3 Deployment Model
- VPS preferred for scraping stability
- API runs as systemd service
- Workers run via cron or systemd timers
- During testing: run workers manually (no schedule)

---

3. Data Model (Supabase)

3.1 articles
Purpose: canonical content items (manual or scraped)
Key fields:
- id (uuid)
- source_url (unique)
- source_website (manual or domain)
- title
- raw_html (raw HTML or extracted text)
- content (optional extracted content)
- summary (LLM summary)
- judge_score (1-10)
- format_assignments (jsonb array)
- processed, scored (bool)
- scraped_at, created_at

3.2 posts
Purpose: AI-generated content per article + format
Key fields:
- article_id
- platform
- content_type
- generating_model
- content (jsonb)
- selected

3.3 performance_metrics
Purpose: engagement tracking

3.4 model_performance
Purpose: track model wins over time

---

4. Intake API

4.1 Endpoints
- GET /health
- POST /intake/text
- POST /intake/file

4.2 /intake/text
Request JSON:
{
  "title": "Optional",
  "text": "Required"
}
Behavior:
- Validate text
- Split by headings
- Fallback chunk by MAX_WORDS
- Insert each chunk into articles

4.3 /intake/file
Request multipart:
- title (optional)
- file (required)
Behavior:
- Save file to temp
- Run scripts/extract_text.py
- Parse sections
- Insert each chunk into articles

4.4 Response
- status: ok
- inserted: count
- ids: list of article ids

---

5. Scraping

5.1 Sources
MVP list (configurable):
- https://www.topky.sk/se/15/Prominenti
- https://www.cas.sk/r/prominenti
- https://www1.pluska.sk/r/soubiznis
- https://refresher.sk/osobnosti
- https://www.startitup.sk/kategoria/kultura/

5.2 Behavior
- Fetch category pages -> category_pages
- Extract article URLs -> article_urls
- Fetch article pages -> articles
- Use unique constraints to prevent duplicates

5.3 Error Handling
- On non-200: log and continue
- On timeout: retry optional

---

6. Extraction Worker (Planned)

Inputs:
- articles where processed=false
Outputs:
- summary, processed=true

Rules:
- Handle HTML or plain text
- Enforce token limits
- Batch processing

---

7. First Judge (Planned)

Inputs:
- articles where processed=true and scored=false
Outputs:
- judge_score, format_assignments, scored=true

Format rules:
- 8-10: headline, carousel, video, podcast
- 6-7: carousel + headline
- 4-5: headline
- 1-3: none

---

8. Generation (Planned)

Inputs:
- articles with format_assignments
Outputs:
- posts rows per model

Constraints:
- generate all requested formats in one call per model
- store structured JSON by format

---

9. Second Judge (Planned)

Inputs:
- posts grouped by article + format
Outputs:
- best selected per format

---

10. Publishing (Planned)

Targets:
- Instagram, Facebook, TikTok, YouTube

Constraints:
- rate limits per platform
- store post_url, posted_at

10.1 Short Video Automation (Planned)
Goal: 1-2 minute vertical videos (9:16).
Pipeline:
- Generate script from summary
- Split script into scenes
- Generate images per scene (low-cost)
- Generate voiceover (TTS)
- Generate captions (ASR)
- Assemble with FFmpeg (images + voice + captions)
Requirement: FFmpeg installed on host

---

11. Monitoring + Testing

11.1 Basic API Tests
- /health ok
- /intake/text inserts rows
- /intake/file inserts rows

11.2 Scraper Tests
- scrape inserts rows
- partial failures do not stop job

11.3 Data Tests
- source_url unique
- processed/scored defaults false

---

12. Configuration
Required:
- SUPABASE_URL
- SUPABASE_KEY

Optional:
- OPENAI_API_KEY
- MANUAL_INTAKE_SCRIPT
- MANUAL_INTAKE_DIR
- MAX_WORDS
- REQUEST_TIMEOUT

---

13. Decisions + Open Questions

Decisions
- Start with website scraping (category pages). Social/video scraping deferred.
- Video format: 9:16 vertical. Start with cheapest acceptable quality.
- Use OpenAI models for early testing; finalize model list later.

Open Questions
- Exact website sources list for MVP
- Final model lineup for extraction/judging/generation
- Publishing platform priority (TikTok/Shorts/IG Reels first?)
- Token/cost budgets per stage

