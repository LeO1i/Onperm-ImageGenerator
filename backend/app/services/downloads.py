from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import MODELS_DIR, ensure_directories
from .models import catalog_by_id, get_model_entry, is_model_downloaded

logger = logging.getLogger(__name__)


def download_catalog_model(model_id: str) -> dict[str, Any]:
    from huggingface_hub import snapshot_download

    entry = catalog_by_id().get(model_id)
    if entry is None:
        raise ValueError(f"Unknown catalog model: {model_id}")

    target = MODELS_DIR / model_id
    ensure_directories()
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    if is_model_downloaded(model_id, entry):
        return _model_api_item(model_id, entry)

    repo_id = entry.get("repo_id")
    if not repo_id:
        raise ValueError(f"Catalog entry {model_id} has no repo_id")

    logger.info("Downloading model %s from %s", model_id, repo_id)
    snapshot_download(
        repo_id=repo_id,
        local_dir=str(target),
        local_dir_use_symlinks=False,
        resume_download=True,
    )
    return _model_api_item(model_id, entry)


def _model_api_item(model_id: str, entry: dict[str, Any]) -> dict[str, Any]:
    from .models import get_models_list

    models = get_models_list()["models"]
    for model in models:
        if model["id"] == model_id:
            return model
    return {
        "id": model_id,
        "label": entry["label"],
        "source": "catalog",
        "status": "ready",
        "compatible": True,
        "family": entry.get("family", "sd15"),
        "disabled_reason": None,
        "size_presets": entry.get("size_presets", []),
    }
