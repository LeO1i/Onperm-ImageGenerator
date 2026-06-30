from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class GpuInfo:
    available: bool
    name: str | None
    driver_version: str | None
    total_vram_mb: int | None
    free_vram_mb: int | None
    compute_capability: tuple[int, int] | None


def detect_gpu() -> GpuInfo:
    name = None
    total_mb = None
    free_mb = None
    compute_capability = None
    available = False

    try:
        import torch

        available = torch.cuda.is_available()
        if available:
            name = torch.cuda.get_device_name(0)
            props = torch.cuda.get_device_properties(0)
            total_mb = int(props.total_memory / (1024 * 1024))
            free_bytes, _ = torch.cuda.mem_get_info(0)
            free_mb = int(free_bytes / (1024 * 1024))
            compute_capability = (props.major, props.minor)
    except Exception as exc:
        logger.info("CUDA detection via PyTorch failed: %s", exc)

    driver_version = _read_nvidia_smi_driver()
    if total_mb is None:
        smi_total, smi_free = _read_nvidia_smi_memory()
        total_mb = smi_total or total_mb
        free_mb = smi_free or free_mb

    return GpuInfo(
        available=available,
        name=name,
        driver_version=driver_version,
        total_vram_mb=total_mb,
        free_vram_mb=free_mb,
        compute_capability=compute_capability,
    )


def _run_nvidia_smi(args: list[str]) -> str | None:
    try:
        result = subprocess.run(
            ["nvidia-smi", *args],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    return None


def _read_nvidia_smi_driver() -> str | None:
    output = _run_nvidia_smi([])
    if not output:
        return None
    for line in output.splitlines():
        if "Driver Version" in line:
            parts = line.split("Driver Version:")
            if len(parts) > 1:
                return parts[1].split()[0]
    return None


def _read_nvidia_smi_memory() -> tuple[int | None, int | None]:
    output = _run_nvidia_smi(
        ["--query-gpu=memory.total,memory.free", "--format=csv,noheader,nounits"]
    )
    if not output:
        return None, None
    try:
        total, free = output.splitlines()[0].split(",")
        return int(total.strip()), int(free.strip())
    except (ValueError, IndexError):
        return None, None


def total_vram_gb(gpu: GpuInfo) -> float | None:
    if gpu.total_vram_mb is None:
        return None
    return gpu.total_vram_mb / 1024
