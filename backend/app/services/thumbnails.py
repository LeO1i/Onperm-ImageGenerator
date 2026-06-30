from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

from ..config import THUMB_SIZE, THUMBS_DIR, ensure_directories

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="thumb")


def thumb_path_for(job_id: str, image_id: str) -> Path:
    return THUMBS_DIR / job_id / f"{image_id}.webp"


def generate_thumbnail(source_path: Path, dest_path: Path) -> Path:
    ensure_directories()
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source_path) as img:
        img = img.convert("RGB")
        img.thumbnail((THUMB_SIZE, THUMB_SIZE), Image.Resampling.LANCZOS)
        img.save(dest_path, format="WEBP", quality=80)
    return dest_path


def schedule_thumbnail(source_path: Path, job_id: str, image_id: str) -> Path:
    dest = thumb_path_for(job_id, image_id)

    def _task() -> Path:
        try:
            return generate_thumbnail(source_path, dest)
        except Exception as exc:
            logger.exception("Thumbnail generation failed: %s", exc)
            return dest

    _executor.submit(_task)
    return dest
