CREATE TABLE IF NOT EXISTS schema_version (
  version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS saved_prompts (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  prompt TEXT NOT NULL,
  negative_prompt TEXT NOT NULL DEFAULT '',
  tags TEXT NOT NULL DEFAULT '[]',
  is_favorite INTEGER NOT NULL DEFAULT 0,
  source_template_id TEXT,
  notes TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_saved_prompts_name ON saved_prompts(name);
CREATE INDEX IF NOT EXISTS idx_saved_prompts_favorite ON saved_prompts(is_favorite);

CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  status TEXT NOT NULL,
  prompt TEXT NOT NULL,
  negative_prompt TEXT NOT NULL DEFAULT '',
  model_id TEXT NOT NULL,
  size_preset_id TEXT NOT NULL,
  width INTEGER NOT NULL,
  height INTEGER NOT NULL,
  steps INTEGER NOT NULL,
  seed INTEGER,
  image_count INTEGER NOT NULL,
  completed_count INTEGER NOT NULL DEFAULT 0,
  error_message TEXT,
  output_directory TEXT NOT NULL,
  created_at TEXT NOT NULL,
  started_at TEXT,
  finished_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);

CREATE TABLE IF NOT EXISTS job_images (
  id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  idx INTEGER NOT NULL,
  seed INTEGER NOT NULL,
  file_path TEXT NOT NULL,
  thumb_path TEXT,
  status TEXT NOT NULL DEFAULT 'completed',
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_job_images_job_id ON job_images(job_id);
