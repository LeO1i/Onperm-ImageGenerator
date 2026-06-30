"""Standalone database package for OnPrem Image Generator."""

from .config import DB_PATH, DATA_DIR, SCHEMA_PATH, ensure_data_dir
from .connection import (
    db_cursor,
    execute,
    fetch_all,
    fetch_one,
    get_connection,
    init_database,
)
from .repositories import jobs as jobs_repo
from .repositories import prompts as prompts_repo

__all__ = [
    "DB_PATH",
    "DATA_DIR",
    "SCHEMA_PATH",
    "ensure_data_dir",
    "db_cursor",
    "execute",
    "fetch_all",
    "fetch_one",
    "get_connection",
    "init_database",
    "jobs_repo",
    "prompts_repo",
]
