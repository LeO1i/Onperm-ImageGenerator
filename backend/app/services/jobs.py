from __future__ import annotations

import asyncio
import json
import logging
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, AsyncIterator

from db.repositories import jobs as jobs_repo
from db.repositories.jobs import mark_interrupted_jobs

from ..config import JOB_ID_PREFIX, THUMBS_DIR, ensure_directories
from .models import catalog_by_id, get_model_entry
from .settings import load_settings, normalize_path

logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_job_id() -> str:
    return f"{JOB_ID_PREFIX}{uuid.uuid4().hex[:12]}"


def _model_label(model_id: str) -> str:
    entry = get_model_entry(model_id)
    if entry:
        return entry.get("label", model_id)
    catalog = catalog_by_id()
    if model_id in catalog:
        return catalog[model_id]["label"]
    return model_id


def _with_model_label(job: dict[str, Any]) -> dict[str, Any]:
    enriched = job.copy()
    enriched["model_label"] = _model_label(job["model_id"])
    return enriched


def list_jobs(
    *,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    rows, total = jobs_repo.list_jobs(status=status, limit=limit, offset=offset)
    return {
        "jobs": [_with_model_label(job) for job in rows],
        "total": total,
    }


def get_job(job_id: str, include_images: bool = True) -> dict[str, Any] | None:
    job = jobs_repo.get_job(job_id, include_images=include_images)
    if job is None:
        return None
    return _with_model_label(job)


def create_job_record(data: dict[str, Any], output_directory: str) -> dict[str, Any]:
    job_id = _new_job_id()
    job = jobs_repo.create_job(job_id, data, output_directory)
    return _with_model_label(job)


def update_job_status(
    job_id: str,
    *,
    status: str | None = None,
    completed_count: int | None = None,
    error_message: str | None = None,
    started: bool = False,
    finished: bool = False,
) -> None:
    jobs_repo.update_job_status(
        job_id,
        status=status,
        completed_count=completed_count,
        error_message=error_message,
        started=started,
        finished=finished,
    )


def add_job_image(
    job_id: str,
    *,
    index: int,
    seed: int,
    file_path: str,
    thumb_path: str | None,
    status: str = "completed",
) -> dict[str, Any]:
    return jobs_repo.add_job_image(
        job_id,
        index=index,
        seed=seed,
        file_path=file_path,
        thumb_path=thumb_path,
        status=status,
    )


def get_job_image(image_id: str) -> dict[str, Any] | None:
    return jobs_repo.get_job_image(image_id)


def cancel_job(job_id: str) -> dict[str, Any] | None:
    job = get_job(job_id, include_images=False)
    if job is None:
        return None
    if job["status"] in {"completed", "failed", "cancelled", "interrupted"}:
        return job
    update_job_status(job_id, status="cancelled", finished=True)
    return get_job(job_id)


def delete_job(job_id: str, delete_files: bool = False) -> bool:
    job = jobs_repo.get_job(job_id, include_images=True)
    if job is None:
        return False

    if delete_files:
        images = job.get("images") or []
        dirs_to_check: set[Path] = set()
        for image in images:
            file_path = Path(image["file_path"])
            if file_path.exists():
                file_path.unlink(missing_ok=True)
            dirs_to_check.add(file_path.parent)
        for directory in dirs_to_check:
            job_json = directory / "job.json"
            if job_json.exists():
                job_json.unlink(missing_ok=True)
            if directory.exists() and not any(directory.iterdir()):
                directory.rmdir()

    thumb_dir = THUMBS_DIR / job_id
    if thumb_dir.exists():
        shutil.rmtree(thumb_dir, ignore_errors=True)

    return jobs_repo.delete_job_record(job_id)


def recent_images(limit: int = 50) -> list[dict[str, Any]]:
    return [
        {
            **row,
            "thumb_url": f"/api/thumbs/{row['id']}",
        }
        for row in jobs_repo.list_recent_images(limit)
    ]


def prune_job_history() -> int:
    settings = load_settings()
    max_days = int(settings.get("history_retention_days", 90))
    max_jobs = int(settings.get("history_retention_max_jobs", 500))
    cutoff = (datetime.now(timezone.utc) - timedelta(days=max_days)).isoformat()

    removed = 0
    for job_id in jobs_repo.list_job_ids_before(cutoff):
        if delete_job(job_id, delete_files=False):
            removed += 1

    total = jobs_repo.count_jobs()
    if total > max_jobs:
        for job_id in jobs_repo.list_oldest_job_ids(total - max_jobs):
            if delete_job(job_id, delete_files=False):
                removed += 1
    return removed


def write_job_json(
    job_dir: Path,
    job: dict[str, Any],
    images: list[dict[str, Any]],
) -> None:
    payload = {
        "job_id": job["id"],
        "prompt": job["prompt"],
        "negative_prompt": job["negative_prompt"],
        "model_id": job["model_id"],
        "size_preset_id": job["size_preset_id"],
        "width": job["width"],
        "height": job["height"],
        "steps": job["steps"],
        "seed": job["seed"],
        "image_count": job["image_count"],
        "images": [
            {
                "index": img["index"],
                "seed": img["seed"],
                "file_name": Path(img["file_path"]).name,
            }
            for img in images
        ],
    }
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "job.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def job_output_dir(output_root: str | Path, job_id: str) -> Path:
    date_prefix = datetime.now(timezone.utc).strftime("%Y%m%d")
    return normalize_path(str(output_root)) / date_prefix / job_id


class JobEventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[asyncio.Queue[dict[str, Any]]]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, job_id: str) -> AsyncIterator[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        async with self._lock:
            self._subscribers.setdefault(job_id, []).append(queue)
        try:
            while True:
                event = await queue.get()
                yield event
                if event.get("type") in {"done", "failed", "cancelled"}:
                    break
        finally:
            async with self._lock:
                subs = self._subscribers.get(job_id, [])
                if queue in subs:
                    subs.remove(queue)

    def publish(self, job_id: str, event: dict[str, Any]) -> None:
        for queue in self._subscribers.get(job_id, []):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("SSE queue full for job %s", job_id)


event_bus = JobEventBus()

__all__ = ["mark_interrupted_jobs"]
