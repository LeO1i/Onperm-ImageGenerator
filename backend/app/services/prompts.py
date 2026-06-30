from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from ..config import TEMPLATES_PATH
from ..db.database import db_cursor, execute, fetch_all, fetch_one


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_templates() -> list[dict[str, Any]]:
    with TEMPLATES_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def _row_to_prompt(row) -> dict[str, Any]:
    tags = json.loads(row["tags"] or "[]")
    return {
        "id": row["id"],
        "name": row["name"],
        "prompt": row["prompt"],
        "negative_prompt": row["negative_prompt"],
        "tags": tags,
        "is_favorite": bool(row["is_favorite"]),
        "source_template_id": row["source_template_id"],
        "notes": row["notes"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_saved_prompts(
    *,
    q: str | None = None,
    tag: str | None = None,
    favorite: bool | None = None,
) -> list[dict[str, Any]]:
    query = "SELECT * FROM saved_prompts WHERE 1=1"
    params: list[Any] = []

    if q:
        query += " AND (name LIKE ? OR prompt LIKE ?)"
        like = f"%{q}%"
        params.extend([like, like])
    if favorite:
        query += " AND is_favorite = 1"
    query += " ORDER BY is_favorite DESC, updated_at DESC"

    rows = fetch_all(query, tuple(params))
    prompts = [_row_to_prompt(row) for row in rows]
    if tag:
        prompts = [p for p in prompts if tag in p["tags"]]
    return prompts


def get_saved_prompt(prompt_id: str) -> dict[str, Any] | None:
    row = fetch_one("SELECT * FROM saved_prompts WHERE id = ?", (prompt_id,))
    return _row_to_prompt(row) if row else None


def create_saved_prompt(data: dict[str, Any]) -> dict[str, Any]:
    now = _utc_now()
    prompt_id = str(uuid.uuid4())
    tags = json.dumps(data.get("tags") or [])
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO saved_prompts (
              id, name, prompt, negative_prompt, tags, is_favorite,
              source_template_id, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                prompt_id,
                data["name"],
                data["prompt"],
                data.get("negative_prompt") or "",
                tags,
                1 if data.get("is_favorite") else 0,
                data.get("source_template_id"),
                data.get("notes"),
                now,
                now,
            ),
        )
    return get_saved_prompt(prompt_id)  # type: ignore[return-value]


def update_saved_prompt(prompt_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
    existing = get_saved_prompt(prompt_id)
    if existing is None:
        return None

    merged = existing.copy()
    merged.update({k: v for k, v in data.items() if v is not None})
    tags = json.dumps(merged.get("tags") or [])
    with db_cursor() as cur:
        cur.execute(
            """
            UPDATE saved_prompts
            SET name = ?, prompt = ?, negative_prompt = ?, tags = ?,
                is_favorite = ?, source_template_id = ?, notes = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                merged["name"],
                merged["prompt"],
                merged.get("negative_prompt") or "",
                tags,
                1 if merged.get("is_favorite") else 0,
                merged.get("source_template_id"),
                merged.get("notes"),
                _utc_now(),
                prompt_id,
            ),
        )
    return get_saved_prompt(prompt_id)


def delete_saved_prompt(prompt_id: str) -> bool:
    execute("DELETE FROM saved_prompts WHERE id = ?", (prompt_id,))
    return True
