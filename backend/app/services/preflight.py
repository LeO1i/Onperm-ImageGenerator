from __future__ import annotations

import importlib.util
import logging
import os
from datetime import datetime, timezone
from typing import Any

from ..config import APP_DATA_ROOT, DATA_DIR, MODELS_DIR, ensure_directories
from .gpu import detect_gpu, total_vram_gb
from .settings import disk_free_gb, ensure_output_directory, load_settings, normalize_path

logger = logging.getLogger(__name__)

_cached_result: dict[str, Any] | None = None


def _item(
    *,
    id: str,
    name: str,
    status: str,
    severity: str,
    message: str,
    fix_hint: str | None = None,
) -> dict[str, Any]:
    return {
        "id": id,
        "name": name,
        "status": status,
        "severity": severity,
        "message": message,
        "fix_hint": fix_hint,
    }


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def run_preflight_checks(force: bool = False) -> dict[str, Any]:
    global _cached_result
    if _cached_result is not None and not force:
        return _cached_result

    ensure_directories()
    gpu = detect_gpu()
    settings = load_settings()
    items: list[dict[str, Any]] = []

    has_nvidia = bool(gpu.name) or gpu.driver_version is not None
    items.append(
        _item(
            id="nvidia_gpu",
            name="NVIDIA GPU present",
            status="pass" if has_nvidia else "fail",
            severity="critical",
            message=(
                f"{gpu.name} detected."
                if gpu.name
                else "No NVIDIA GPU found."
            ),
            fix_hint=None
            if has_nvidia
            else "Install an NVIDIA GPU and the latest Windows driver.",
        )
    )

    items.append(
        _item(
            id="cuda_available",
            name="CUDA available",
            status="pass" if gpu.available else "fail",
            severity="critical",
            message=(
                "PyTorch can access CUDA."
                if gpu.available
                else "PyTorch cannot access CUDA."
            ),
            fix_hint=None
            if gpu.available
            else (
                "Install the latest NVIDIA driver, then install the CUDA-enabled "
                "PyTorch build for Windows."
            ),
        )
    )

    items.append(
        _item(
            id="nvidia_driver",
            name="NVIDIA driver",
            status="pass" if gpu.driver_version else "fail",
            severity="critical",
            message=(
                f"Driver version {gpu.driver_version}."
                if gpu.driver_version
                else "NVIDIA driver not detected."
            ),
            fix_hint=None
            if gpu.driver_version
            else "Install the latest NVIDIA driver from nvidia.com.",
        )
    )

    total_gb = total_vram_gb(gpu)
    items.append(
        _item(
            id="vram_total",
            name="GPU memory",
            status="pass" if total_gb is None or total_gb >= 8 else "warn",
            severity="warning",
            message=(
                f"{gpu.total_vram_mb} MB total VRAM detected."
                if gpu.total_vram_mb
                else "Could not read GPU VRAM."
            ),
            fix_hint=None
            if total_gb is None or total_gb >= 8
            else "Less than 8 GB VRAM — SDXL and large presets may be unavailable.",
        )
    )

    items.append(
        _item(
            id="vram_free",
            name="Free VRAM now",
            status=(
                "pass"
                if gpu.free_vram_mb is None or gpu.free_vram_mb >= 4096
                else "warn"
            ),
            severity="warning",
            message=(
                f"{gpu.free_vram_mb} MB free VRAM."
                if gpu.free_vram_mb is not None
                else "Could not read free VRAM."
            ),
            fix_hint=None
            if gpu.free_vram_mb is None or gpu.free_vram_mb >= 4096
            else "Close other GPU applications before generating.",
        )
    )

    app_data_ok = False
    try:
        APP_DATA_ROOT.mkdir(parents=True, exist_ok=True)
        test = APP_DATA_ROOT / ".write_test"
        test.write_text("ok", encoding="utf-8")
        test.unlink(missing_ok=True)
        app_data_ok = True
    except OSError:
        app_data_ok = False

    items.append(
        _item(
            id="app_data_writable",
            name="App data directory",
            status="pass" if app_data_ok else "fail",
            severity="critical",
            message=(
                f"{APP_DATA_ROOT} is writable."
                if app_data_ok
                else f"Cannot write to {APP_DATA_ROOT}."
            ),
            fix_hint=None
            if app_data_ok
            else "Check permissions for your AppData folder.",
        )
    )

    output_path, output_warning = ensure_output_directory(settings)
    output_ok = output_warning is None
    items.append(
        _item(
            id="output_dir_writable",
            name="Output directory",
            status="pass" if output_ok else "fail",
            severity="critical",
            message=(
                f"Output directory {output_path} is writable."
                if output_ok
                else output_warning or "Output directory is not writable."
            ),
            fix_hint=None
            if output_ok
            else "Choose a writable folder in Settings.",
        )
    )

    models_ok = False
    try:
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        test = MODELS_DIR / ".write_test"
        test.write_text("ok", encoding="utf-8")
        test.unlink(missing_ok=True)
        models_ok = True
    except OSError:
        models_ok = False

    items.append(
        _item(
            id="models_dir_writable",
            name="Models directory",
            status="pass" if models_ok else "fail",
            severity="critical",
            message=(
                f"{MODELS_DIR} is writable."
                if models_ok
                else f"Cannot write to {MODELS_DIR}."
            ),
            fix_hint=None if models_ok else "Check permissions for the models folder.",
        )
    )

    models_free = disk_free_gb(MODELS_DIR)
    items.append(
        _item(
            id="disk_space_models",
            name="Disk space for models",
            status="pass" if models_free is None or models_free >= 10 else "warn",
            severity="warning",
            message=(
                f"{models_free:.1f} GB free on models drive."
                if models_free is not None
                else "Could not read disk space."
            ),
            fix_hint=None
            if models_free is None or models_free >= 10
            else "Low disk space may cause model downloads to fail.",
        )
    )

    output_free = disk_free_gb(output_path)
    items.append(
        _item(
            id="disk_space_output",
            name="Disk space for output",
            status="pass" if output_free is None or output_free >= 1 else "warn",
            severity="warning",
            message=(
                f"{output_free:.1f} GB free on output drive."
                if output_free is not None
                else "Could not read disk space."
            ),
            fix_hint=None
            if output_free is None or output_free >= 1
            else "Low disk space may cause generation to fail.",
        )
    )

    sqlite_ok = False
    try:
        from ..db.database import init_database

        init_database()
        sqlite_ok = DATA_DIR.joinpath("app.db").exists()
    except Exception as exc:
        logger.exception("SQLite init failed: %s", exc)
        sqlite_ok = False

    items.append(
        _item(
            id="sqlite_ok",
            name="Local database",
            status="pass" if sqlite_ok else "fail",
            severity="critical",
            message=(
                "SQLite database is ready."
                if sqlite_ok
                else "Database initialization failed."
            ),
            fix_hint=None if sqlite_ok else "Check write permissions for the data folder.",
        )
    )

    pytorch_ok = _module_available("torch")
    items.append(
        _item(
            id="pytorch_ok",
            name="PyTorch",
            status="pass" if pytorch_ok else "fail",
            severity="critical",
            message="PyTorch import succeeded." if pytorch_ok else "PyTorch is not installed.",
            fix_hint=None if pytorch_ok else "Install backend Python dependencies.",
        )
    )

    diffusers_ok = _module_available("diffusers")
    items.append(
        _item(
            id="diffusers_ok",
            name="Diffusers",
            status="pass" if diffusers_ok else "fail",
            severity="critical",
            message=(
                "Diffusers import available."
                if diffusers_ok
                else "Diffusers library is missing."
            ),
            fix_hint=None if diffusers_ok else "Install diffusers and transformers.",
        )
    )

    critical_passed = all(
        item["status"] != "fail"
        for item in items
        if item["severity"] == "critical"
    )
    warning_count = sum(1 for item in items if item["status"] == "warn")

    result = {
        "ready": critical_passed and warning_count == 0,
        "critical_passed": critical_passed,
        "warning_count": warning_count,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "items": items,
        "gpu_name": gpu.name,
        "driver_version": gpu.driver_version,
        "total_vram_mb": gpu.total_vram_mb,
        "free_vram_mb": gpu.free_vram_mb,
    }
    _cached_result = result
    return result


def get_cached_preflight() -> dict[str, Any]:
    if _cached_result is None:
        return run_preflight_checks(force=True)
    return _cached_result


def invalidate_preflight_cache() -> None:
    global _cached_result
    _cached_result = None
