from __future__ import annotations

import asyncio
import json
import logging
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, AsyncIterator

from ..config import JOB_ID_PREFIX, THUMBS_DIR, ensure_directories
from ..db.database import db_cursor, execute, fetch_all, fetch_one
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


def _row_to_image(row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "job_id": row["job_id"],
        "index": row["idx"],
        "seed": row["seed"],
        "file_path": row["file_path"],
        "thumb_path": row["thumb_path"],
        "status": row["status"],
        "created_at": row["created_at"],
    }


def _row_to_job(row, include_images: bool = False) -> dict[str, Any]:
    job = {
        "id": row["id"],
        "status": row["status"],
        "prompt": row["prompt"],
        "negative_prompt": row["negative_prompt"],
        "model_id": row["model_id"],
        "model_label": _model_label(row["model_id"]),
        "size_preset_id": row["size_preset_id"],
        "width": row["width"],
        "height": row["height"],
        "steps": row["steps"],
        "seed": row["seed"],
        "image_count": row["image_count"],
        "completed_count": row["completed_count"],
        "error_message": row["error_message"],
        "output_directory": row["output_directory"],
        "created_at": row["created_at"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
    }
    if include_images:
        images = fetch_all(
            "SELECT * FROM job_images WHERE job_id = ? ORDER BY idx",
            (row["id"],),
        )
        job["images"] = [_row_to_image(img) for img in images]
    return job


def list_jobs(
    *,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    query = "SELECT * FROM jobs"
    params: list[Any] = []
    if status:
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = fetch_all(query, tuple(params))
    count_query = "SELECT COUNT(*) AS c FROM jobs"
    count_params: tuple[Any, ...] = ()
    if status:
        count_query += " WHERE status = ?"
        count_params = (status,)
    total = fetch_one(count_query, count_params)["c"]
    return {
        "jobs": [_row_to_job(row) for row in rows],
        "total": total,
    }


def get_job(job_id: str, include_images: bool = True) -> dict[str, Any] | None:
    row = fetch_one("SELECT * FROM jobs WHERE id = ?", (job_id,))
    if row is None:
        return None
    return _row_to_job(row, include_images=include_images)


def create_job_record(data: dict[str, Any], output_directory: str) -> dict[str, Any]:
    job_id = _new_job_id()
    now = _utc_now()
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO jobs (
              id, status, prompt, negative_prompt, model_id, size_preset_id,
              width, height, steps, seed, image_count, completed_count,
              error_message, output_directory, created_at
            ) VALUES (?, 'queued', ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, ?, ?)
            """,
            (
                job_id,
                data["prompt"],
                data.get("negative_prompt") or "",
                data["model_id"],
                data["size_preset_id"],
                data["width"],
                data["height"],
                data["steps"],
                data.get("seed"),
                data["image_count"],
                output_directory,
                now,
            ),
        )
    return get_job(job_id)  # type: ignore[return-value]


def update_job_status(
    job_id: str,
    *,
    status: str | None = None,
    completed_count: int | None = None,
    error_message: str | None = None,
    started: bool = False,
    finished: bool = False,
) -> None:
    fields: list[str] = []
    params: list[Any] = []
    if status is not None:
        fields.append("status = ?")
        params.append(status)
    if completed_count is not None:
        fields.append("completed_count = ?")
        params.append(completed_count)
    if error_message is not None:
        fields.append("error_message = ?")
        params.append(error_message)
    if started:
        fields.append("started_at = ?")
        params.append(_utc_now())
    if finished:
        fields.append("finished_at = ?")
        params.append(_utc_now())
    if not fields:
        return
    params.append(job_id)
    execute(f"UPDATE jobs SET {', '.join(fields)} WHERE id = ?", tuple(params))


def add_job_image(
    job_id: str,
    *,
    index: int,
    seed: int,
    file_path: str,
    thumb_path: str | None,
    status: str = "completed",
) -> dict[str, Any]:
    image_id = str(uuid.uuid4())
    now = _utc_now()
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO job_images (id, job_id, idx, seed, file_path, thumb_path, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (image_id, job_id, index, seed, file_path, thumb_path, status, now),
        )
    row = fetch_one("SELECT * FROM job_images WHERE id = ?", (image_id,))
    return _row_to_image(row)


def get_job_image(image_id: str) -> dict[str, Any] | None:
    row = fetch_one("SELECT * FROM job_images WHERE id = ?", (image_id,))
    return _row_to_image(row) if row else None


def cancel_job(job_id: str) -> dict[str, Any] | None:
    job = get_job(job_id, include_images=False)
    if job is None:
        return None
    if job["status"] in {"completed", "failed", "cancelled", "interrupted"}:
        return job
    update_job_status(job_id, status="cancelled", finished=True)
    return get_job(job_id)


def delete_job(job_id: str, delete_files: bool = False) -> bool:
    job = get_job(job_id, include_images=True)
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

    execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    return True


def recent_images(limit: int = 50) -> list[dict[str, Any]]:
    rows = fetch_all(
        """
        SELECT ji.id, ji.job_id, ji.idx, ji.created_at
        FROM job_images ji
        JOIN jobs j ON j.id = ji.job_id
        WHERE ji.status = 'completed'
        ORDER BY ji.created_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    return [
        {
            "id": row["id"],
            "job_id": row["job_id"],
            "index": row["idx"],
            "thumb_url": f"/api/thumbs/{row['id']}",
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def prune_job_history() -> int:
    settings = load_settings()
    max_days = int(settings.get("history_retention_days", 90))
    max_jobs = int(settings.get("history_retention_max_jobs", 500))
    cutoff = (datetime.now(timezone.utc) - timedelta(days=max_days)).isoformat()

    old_jobs = fetch_all(
        "SELECT id FROM jobs WHERE created_at < ? ORDER BY created_at ASC",
        (cutoff,),
    )
    removed = 0
    for row in old_jobs:
        if delete_job(row["id"], delete_files=False):
            removed += 1

    total = fetch_one("SELECT COUNT(*) AS c FROM jobs")["c"]
    if total > max_jobs:
        excess = fetch_all(
            """
            SELECT id FROM jobs
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (total - max_jobs,),
        )
        for row in excess:
            if delete_job(row["id"], delete_files=False):
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
