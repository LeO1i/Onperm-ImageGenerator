from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from ..connection import db_cursor, execute, fetch_all, fetch_one


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _row_to_job(row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "status": row["status"],
        "prompt": row["prompt"],
        "negative_prompt": row["negative_prompt"],
        "model_id": row["model_id"],
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


def list_jobs(
    *,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
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
    return [_row_to_job(row) for row in rows], total


def get_job(job_id: str, *, include_images: bool = False) -> dict[str, Any] | None:
    row = fetch_one("SELECT * FROM jobs WHERE id = ?", (job_id,))
    if row is None:
        return None
    job = _row_to_job(row)
    if include_images:
        images = fetch_all(
            "SELECT * FROM job_images WHERE job_id = ? ORDER BY idx",
            (job_id,),
        )
        job["images"] = [_row_to_image(image) for image in images]
    return job


def create_job(job_id: str, data: dict[str, Any], output_directory: str) -> dict[str, Any]:
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
            INSERT INTO job_images (
              id, job_id, idx, seed, file_path, thumb_path, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (image_id, job_id, index, seed, file_path, thumb_path, status, now),
        )
    row = fetch_one("SELECT * FROM job_images WHERE id = ?", (image_id,))
    return _row_to_image(row)


def get_job_image(image_id: str) -> dict[str, Any] | None:
    row = fetch_one("SELECT * FROM job_images WHERE id = ?", (image_id,))
    return _row_to_image(row) if row else None


def delete_job_record(job_id: str) -> bool:
    row = fetch_one("SELECT id FROM jobs WHERE id = ?", (job_id,))
    if row is None:
        return False
    execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    return True


def list_recent_images(limit: int = 50) -> list[dict[str, Any]]:
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
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def mark_interrupted_jobs() -> int:
    with db_cursor() as cur:
        cur.execute(
            """
            UPDATE jobs
            SET status = 'interrupted',
                finished_at = COALESCE(finished_at, datetime('now'))
            WHERE status IN ('running', 'queued')
            """
        )
        return cur.rowcount


def list_job_ids_before(cutoff: str) -> list[str]:
    rows = fetch_all(
        "SELECT id FROM jobs WHERE created_at < ? ORDER BY created_at ASC",
        (cutoff,),
    )
    return [row["id"] for row in rows]


def count_jobs() -> int:
    return fetch_one("SELECT COUNT(*) AS c FROM jobs")["c"]


def list_oldest_job_ids(limit: int) -> list[str]:
    rows = fetch_all(
        """
        SELECT id FROM jobs
        ORDER BY created_at ASC
        LIMIT ?
        """,
        (limit,),
    )
    return [row["id"] for row in rows]
