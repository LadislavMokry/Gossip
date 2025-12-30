# Repository Guidelines

## Project Structure & Module Organization
This repo now uses a Python-first architecture (FastAPI + worker scripts) for manual intake and scraping. n8n workflows are deprecated and kept only as historical reference.

- Python app: `app/` (FastAPI intake API + worker scripts).
- Workflow exports (legacy, reference only): `workflows/scraper-hourly-collection.json`, `workflows/link-extractor.json`, `workflows/cleanup-raw-html.json`, `workflows/test-supabase-connection.json`, `workflows/manual-intake.json`.
- Database schema: `db/supabase-schema.sql` (tables for articles, posts, metrics).
- Guides and specs: `docs/SETUP-GUIDE.md`, `docs/scraper-workflow-quick-start.md`, `docs/slovak-gossip-automation-spec (1).md`, `docs/implementation-plan.md`, `docs/todo.md`, `docs/manual-intake.md`.
- Agent/n8n guidance: `CLAUDE.md` and `n8n-skills/` (reference only).

## Build, Test, and Development Commands
There is no build step or test runner in this repo.

- Install Python deps: `pip install -r requirements.txt`
- Run API locally: `uvicorn app.main:app --reload --port 8000`
- Run scraper once: `python -m app.worker scrape`
- Run scraper loop: `python -m app.worker scrape-loop --interval 3600`
- Apply schema by running `db/supabase-schema.sql` in the Supabase SQL Editor.

## Coding Style & Naming Conventions
- Python files use 4-space indentation.
- JSON files use 2-space indentation; keep exports consistent.
- Legacy workflow files use kebab-case names (example: `workflows/scraper-hourly-collection.json`).

## Testing Guidelines
- Validate Supabase connectivity with a simple API call or SQL query.
- Smoke-test API endpoints: `/health`, `/intake/text`, `/intake/file`.
- Validate data with SQL queries in the Supabase dashboard.

## Commit & Pull Request Guidelines
- History uses short, sentence-style messages without a strict convention.
- Keep commits scoped and descriptive (example: `Add FastAPI intake endpoints`).
- PRs should include: summary, schema changes (if any), and test notes.

## Security & Configuration Tips
- Store secrets in `.env` or `.env.local`; never commit API keys.
- Use the Supabase anon/public key for the API; reserve service_role for admin tasks.
- See `docs/SETUP-GUIDE.md` for credential setup and safety notes.
