from __future__ import annotations

from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "app.db"
SCHEMA_PATH = PACKAGE_ROOT / "schema.sql"
MIGRATIONS_DIR = PACKAGE_ROOT / "migrations"

SCHEMA_VERSION = 1


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
