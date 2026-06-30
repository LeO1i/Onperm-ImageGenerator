from __future__ import annotations

import os
import platform
from pathlib import Path

APP_NAME = "OnPremImageGenerator"
HOST = "127.0.0.1"
PORT = 8000
VRAM_HEADROOM_GB = 0.75
DEFAULT_STEPS = 25
THUMB_SIZE = 256
JOB_ID_PREFIX = "job_"
MAX_IMAGES_PER_JOB = 10

PACKAGE_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = PACKAGE_ROOT.parent
PROJECT_ROOT = BACKEND_ROOT.parent
DATA_DIR = PROJECT_ROOT / "data"
CONFIG_DIR = PROJECT_ROOT / "config"
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
CATALOG_PATH = PACKAGE_ROOT / "data" / "models.catalog.json"
TEMPLATES_PATH = PACKAGE_ROOT / "data" / "prompt_templates.json"
SCHEMA_PATH = PACKAGE_ROOT / "db" / "schema.sql"


def _user_home() -> Path:
    home = os.environ.get("HOME") or os.environ.get("USERPROFILE")
    if home:
        return Path(home)
    return Path.cwd()


def get_app_data_root() -> Path:
    if platform.system() == "Windows":
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else _user_home() / "AppData" / "Roaming"
        return base / APP_NAME
    return _user_home() / ".local" / "share" / APP_NAME


APP_DATA_ROOT = get_app_data_root()
MODELS_DIR = APP_DATA_ROOT / "models"
THUMBS_DIR = APP_DATA_ROOT / "thumbs"
LOGS_DIR = APP_DATA_ROOT / "logs"
PID_FILE = APP_DATA_ROOT / "app.pid"
LOCAL_MODELS_CACHE = APP_DATA_ROOT / "local_models_cache.json"
SETTINGS_PATH = CONFIG_DIR / "settings.json"
DB_PATH = DATA_DIR / "app.db"


def default_output_directory() -> Path:
    return _user_home() / APP_NAME / "outputs"


def ensure_directories() -> None:
    for path in (
        DATA_DIR,
        CONFIG_DIR,
        APP_DATA_ROOT,
        MODELS_DIR,
        THUMBS_DIR,
        LOGS_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)
