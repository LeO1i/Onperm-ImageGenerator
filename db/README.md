# Database package

Standalone SQLite layer for the OnPrem Image Generator. Kept separate from the FastAPI backend so schema, migrations, and repositories can be maintained independently.

## Layout

```
db/
├── config.py           # DB file path and schema location
├── connection.py       # SQLite connection, WAL mode, init
├── schema.sql          # Current schema (v1)
├── migrations/         # Future incremental SQL scripts
└── repositories/
    ├── jobs.py         # jobs + job_images tables
    └── prompts.py      # saved_prompts table
```

## Database file

Runtime database: `data/app.db` (project root, gitignored).

## Usage from backend

The backend imports this package via `PYTHONPATH` pointing at the project root:

```python
from db import init_database, jobs_repo, prompts_repo
from db.repositories.jobs import mark_interrupted_jobs
```

## Migrations

`schema.sql` is applied on startup via `init_database()`. For future schema changes, add numbered scripts under `migrations/` and bump `SCHEMA_VERSION` in `db/config.py`.
