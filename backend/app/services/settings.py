from __future__ import annotations

import json
import logging
import os
import platform
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import (
    CONFIG_DIR,
    MODELS_DIR,
    SETTINGS_PATH,
    default_output_directory,
    ensure_directories,
)
from .gpu import detect_gpu

logger = logging.getLogger(__name__)

DEFAULT_SETTINGS: dict[str, Any] = {
    "output_directory": "",
    "last_model_id": None,
    "last_size_preset_id": None,
    "last_steps": 25,
    "history_retention_days": 90,
    "history_retention_max_jobs": 500,
    "log_retention_days": 30,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_settings() -> dict[str, Any]:
    ensure_directories()
    if not SETTINGS_PATH.exists():
        settings = DEFAULT_SETTINGS.copy()
        settings["output_directory"] = str(default_output_directory())
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with SETTINGS_PATH.open("w", encoding="utf-8") as fh:
            json.dump(settings, fh, indent=2)
        return settings.copy()

    with SETTINGS_PATH.open(encoding="utf-8") as fh:
        data = json.load(fh)

    merged = DEFAULT_SETTINGS.copy()
    merged.update(data)
    return merged


def save_settings(settings: dict[str, Any]) -> dict[str, Any]:
    ensure_directories()
    current = load_settings()
    current.update(settings)
    if not current.get("output_directory"):
        current["output_directory"] = str(default_output_directory())

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with SETTINGS_PATH.open("w", encoding="utf-8") as fh:
        json.dump(current, fh, indent=2)
    return current.copy()


def normalize_path(path_str: str) -> Path:
    path = Path(path_str).expanduser()
    if not path.is_absolute():
        path = path.resolve()
    return path


def validate_output_directory(path_str: str) -> tuple[bool, str | None]:
    try:
        path = normalize_path(path_str)
    except OSError as exc:
        return False, f"Invalid path: {exc}"

    protected = {
        Path("C:/Windows"),
        Path("C:/Program Files"),
        Path("C:/Program Files (x86)"),
    }
    if platform.system() == "Windows":
        for root in protected:
            try:
                if path.is_relative_to(root):
                    return False, "Cannot use a system-protected directory."
            except ValueError:
                continue

    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return False, f"Cannot create directory: {exc}"

    test_file = path / ".write_test"
    try:
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink(missing_ok=True)
    except OSError:
        return False, "Cannot write to this folder."

    return True, None


def ensure_output_directory(settings: dict[str, Any] | None = None) -> tuple[Path, str | None]:
    settings = settings or load_settings()
    path_str = settings.get("output_directory") or str(default_output_directory())
    valid, message = validate_output_directory(path_str)
    if valid:
        return normalize_path(path_str), None

    fallback = default_output_directory()
    valid_fallback, _ = validate_output_directory(str(fallback))
    if valid_fallback:
        save_settings({"output_directory": str(fallback)})
        return fallback, message
    return fallback, message or "Output directory is not writable."


def browse_output_directory() -> str | None:
    if platform.system() == "Windows":
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            selected = filedialog.askdirectory()
            root.destroy()
            return selected or None
        except Exception as exc:
            logger.warning("Folder browse failed: %s", exc)
            return None
    return None


def disk_free_gb(path: Path) -> float | None:
    try:
        usage = shutil.disk_usage(path)
        return usage.free / (1024**3)
    except OSError:
        return None


def update_last_form_values(
    *,
    model_id: str | None = None,
    size_preset_id: str | None = None,
    steps: int | None = None,
) -> None:
    patch: dict[str, Any] = {}
    if model_id is not None:
        patch["last_model_id"] = model_id
    if size_preset_id is not None:
        patch["last_size_preset_id"] = size_preset_id
    if steps is not None:
        patch["last_steps"] = steps
    if patch:
        save_settings(patch)
