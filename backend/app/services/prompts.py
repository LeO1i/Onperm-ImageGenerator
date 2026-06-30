from __future__ import annotations

import json
from typing import Any

from db.repositories import prompts as prompts_repo

from ..config import TEMPLATES_PATH


def load_templates() -> list[dict[str, Any]]:
    with TEMPLATES_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def list_saved_prompts(
    *,
    q: str | None = None,
    tag: str | None = None,
    favorite: bool | None = None,
) -> list[dict[str, Any]]:
    return prompts_repo.list_saved_prompts(q=q, tag=tag, favorite=favorite)


def get_saved_prompt(prompt_id: str) -> dict[str, Any] | None:
    return prompts_repo.get_saved_prompt(prompt_id)


def create_saved_prompt(data: dict[str, Any]) -> dict[str, Any]:
    return prompts_repo.create_saved_prompt(data)


def update_saved_prompt(prompt_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
    return prompts_repo.update_saved_prompt(prompt_id, data)


def delete_saved_prompt(prompt_id: str) -> bool:
    prompts_repo.delete_saved_prompt(prompt_id)
    return True
