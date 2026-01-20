-- Add pipeline_runs table for pipeline metrics
CREATE TABLE IF NOT EXISTS pipeline_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
  run_type TEXT DEFAULT 'pipeline',
  status TEXT DEFAULT 'ok',
  scrape_count INTEGER DEFAULT 0,
  ingest_count INTEGER DEFAULT 0,
  extract_count INTEGER DEFAULT 0,
  judge_count INTEGER DEFAULT 0,
  dedupe_count INTEGER DEFAULT 0,
  unusable_count INTEGER DEFAULT 0,
  started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  finished_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_project_id ON pipeline_runs(project_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started_at ON pipeline_runs(started_at DESC);
