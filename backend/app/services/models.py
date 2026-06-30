from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import (
    APP_DATA_ROOT,
    CATALOG_PATH,
    LOCAL_MODELS_CACHE,
    MODELS_DIR,
    VRAM_HEADROOM_GB,
    ensure_directories,
)
from .gpu import GpuInfo, detect_gpu, total_vram_gb
from .settings import disk_free_gb, load_settings, normalize_path

logger = logging.getLogger(__name__)

_gpu_cache: GpuInfo | None = None


def get_gpu_info(refresh: bool = False) -> GpuInfo:
    global _gpu_cache
    if _gpu_cache is None or refresh:
        _gpu_cache = detect_gpu()
    return _gpu_cache


def load_catalog() -> list[dict[str, Any]]:
    with CATALOG_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def catalog_by_id() -> dict[str, dict[str, Any]]:
    return {entry["id"]: entry for entry in load_catalog()}


def _model_local_path(model_id: str, entry: dict[str, Any]) -> Path:
    return MODELS_DIR / model_id


def is_model_downloaded(model_id: str, entry: dict[str, Any] | None = None) -> bool:
    entry = entry or catalog_by_id().get(model_id)
    if entry is None:
        local_path = MODELS_DIR / model_id
        if local_path.is_dir() and (local_path / "model_index.json").exists():
            return True
        safetensors = list(local_path.glob("*.safetensors")) if local_path.exists() else []
        return bool(safetensors)
    path = _model_local_path(model_id, entry)
    if not path.exists():
        return False
    if (path / "model_index.json").exists():
        return True
    return any(path.glob("*.safetensors"))


def get_compatible_presets(
    entry: dict[str, Any],
    effective_vram_gb: float | None,
) -> list[dict[str, Any]]:
    presets: list[dict[str, Any]] = []
    for preset in entry.get("size_presets", []):
        item = dict(preset)
        if effective_vram_gb is None:
            item["compatible"] = True
            item["disabled_reason"] = None
        else:
            fits = effective_vram_gb + VRAM_HEADROOM_GB >= preset["min_vram_gb"]
            item["compatible"] = fits
            item["disabled_reason"] = (
                None if fits else f"Requires {preset['min_vram_gb']} GB VRAM"
            )
        presets.append(item)
    return presets


def _effective_vram_gb(gpu: GpuInfo) -> float | None:
    total = total_vram_gb(gpu)
    if total is None:
        return None
    return max(0.0, total - VRAM_HEADROOM_GB)


def _catalog_item_to_api(
    entry: dict[str, Any],
    gpu: GpuInfo,
    effective_vram_gb: float | None,
) -> dict[str, Any]:
    downloaded = is_model_downloaded(entry["id"], entry)
    presets = get_compatible_presets(entry, effective_vram_gb)
    any_preset_fits = any(p.get("compatible", True) for p in presets)
    min_model_vram = entry.get("min_vram_gb", 6)
    compatible = any_preset_fits and (
        effective_vram_gb is None or effective_vram_gb + VRAM_HEADROOM_GB >= min_model_vram
    )
    disabled_reason = None
    if not compatible:
        disabled_reason = f"Requires at least {min_model_vram} GB VRAM"
    elif not any_preset_fits:
        disabled_reason = "No compatible size presets for this GPU"

    return {
        "id": entry["id"],
        "label": entry["label"],
        "source": "catalog",
        "status": "ready" if downloaded else "download",
        "compatible": compatible,
        "family": entry.get("family", "sd15"),
        "disabled_reason": disabled_reason,
        "size_presets": presets,
    }


def load_local_models_cache() -> list[dict[str, Any]]:
    ensure_directories()
    if not LOCAL_MODELS_CACHE.exists():
        return []
    try:
        with LOCAL_MODELS_CACHE.open(encoding="utf-8") as fh:
            data = json.load(fh)
        return data.get("models", [])
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read local models cache: %s", exc)
        return []


def save_local_models_cache(models: list[dict[str, Any]]) -> None:
    ensure_directories()
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "models": models,
    }
    with LOCAL_MODELS_CACHE.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


def _infer_family_from_path(path: Path) -> str:
    name = path.name.lower()
    if "sdxl" in name or "xl" in name:
        return "sdxl"
    return "sd15"


def _default_presets_for_family(family: str) -> list[dict[str, Any]]:
    catalog = load_catalog()
    for entry in catalog:
        if entry.get("family") == family:
            return entry.get("size_presets", [])
    return catalog[0].get("size_presets", []) if catalog else []


def scan_local_models_folder(gpu: GpuInfo | None = None) -> list[dict[str, Any]]:
    gpu = gpu or get_gpu_info()
    effective_vram_gb = _effective_vram_gb(gpu)
    catalog_ids = set(catalog_by_id().keys())
    discovered: list[dict[str, Any]] = []

    if not MODELS_DIR.exists():
        return discovered

    for child in sorted(MODELS_DIR.iterdir()):
        if not child.is_dir() and child.suffix.lower() != ".safetensors":
            continue
        if child.is_dir() and child.name in catalog_ids:
            continue

        if child.is_dir():
            if not (child / "model_index.json").exists() and not list(child.glob("*.safetensors")):
                continue
            model_id = f"local-{child.name}"
            label = child.name
            family = _infer_family_from_path(child)
        else:
            model_id = f"local-{child.stem}"
            label = child.stem
            family = _infer_family_from_path(child)

        presets = get_compatible_presets(
            {"size_presets": _default_presets_for_family(family)},
            effective_vram_gb,
        )
        discovered.append(
            {
                "id": model_id,
                "label": label,
                "source": "local",
                "status": "unknown",
                "compatible": True,
                "family": family,
                "disabled_reason": None,
                "path": str(child),
                "size_presets": presets,
            }
        )

    save_local_models_cache(discovered)
    return discovered


def get_models_list() -> dict[str, Any]:
    gpu = get_gpu_info()
    effective_vram_gb = _effective_vram_gb(gpu)
    catalog_items = [
        _catalog_item_to_api(entry, gpu, effective_vram_gb) for entry in load_catalog()
    ]
    local_items = load_local_models_cache()
    for item in local_items:
        presets = item.get("size_presets") or get_compatible_presets(
            {"size_presets": _default_presets_for_family(item.get("family", "sd15"))},
            effective_vram_gb,
        )
        item["size_presets"] = presets
    return {
        "models": catalog_items + local_items,
        "total_vram_gb": total_vram_gb(gpu),
    }


def refresh_models() -> dict[str, Any]:
    scan_local_models_folder()
    return get_models_list()


def get_model_entry(model_id: str) -> dict[str, Any] | None:
    catalog = catalog_by_id()
    if model_id in catalog:
        return catalog[model_id]
    for item in load_local_models_cache():
        if item["id"] == model_id:
            return item
    return None


def resolve_model_path(model_id: str) -> Path | None:
    catalog = catalog_by_id()
    if model_id in catalog:
        path = MODELS_DIR / model_id
        return path if path.exists() else None
    for item in load_local_models_cache():
        if item["id"] == model_id:
            return Path(item["path"])
    return None
