from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Callable

from ..config import MAX_IMAGES_PER_JOB
from .generation import GenerationRequest, run_generation, suggest_smaller_preset, _unload_pipeline
from .jobs import (
    add_job_image,
    event_bus,
    get_job,
    update_job_status,
)
from .models import is_model_downloaded, catalog_by_id
from .preflight import run_preflight_checks
from .settings import ensure_output_directory, update_last_form_values
from .thumbnails import generate_thumbnail, thumb_path_for

logger = logging.getLogger(__name__)

_cancel_flags: dict[str, threading.Event] = {}
_worker_lock = threading.Lock()
_active_job_id: str | None = None


def _set_cancel_flag(job_id: str) -> threading.Event:
    event = threading.Event()
    _cancel_flags[job_id] = event
    return event


def request_cancel(job_id: str) -> None:
    flag = _cancel_flags.get(job_id)
    if flag:
        flag.set()


def _publish(job_id: str, event: dict) -> None:
    try:
        event_bus.publish(job_id, event)
    except Exception as exc:
        logger.warning("Failed to publish SSE event: %s", exc)


def _process_job(job_id: str, payload: dict) -> None:
    global _active_job_id
    cancel_flag = _set_cancel_flag(job_id)

    def should_cancel() -> bool:
        return cancel_flag.is_set()

    try:
        update_job_status(job_id, status="running", started=True)
        output_root, _ = ensure_output_directory()
        from .jobs import job_output_dir

        output_dir = job_output_dir(output_root, job_id)

        request = GenerationRequest(
            job_id=job_id,
            prompt=payload["prompt"],
            negative_prompt=payload.get("negative_prompt") or "",
            model_id=payload["model_id"],
            width=int(payload["width"]),
            height=int(payload["height"]),
            steps=int(payload.get("steps") or 25),
            seed=payload.get("seed"),
            image_count=int(payload["image_count"]),
            output_dir=output_dir,
            size_preset_id=payload["size_preset_id"],
        )

        completed = 0

        def on_step(step: int, total_steps: int, image_index: int) -> None:
            progress = int(
                ((image_index - 1) / request.image_count) * 100
                + (step / max(total_steps, 1)) * (100 / request.image_count)
            )
            _publish(
                job_id,
                {
                    "type": "step",
                    "job_id": job_id,
                    "step": step,
                    "total_steps": total_steps,
                    "image_index": image_index,
                    "progress": min(progress, 99),
                },
            )

        def on_image(image_index: int, seed: int, file_path: str) -> None:
            nonlocal completed
            source = Path(file_path)
            image_id = None
            thumb_dest = thumb_path_for(job_id, f"{job_id}_{image_index}")
            try:
                generate_thumbnail(source, thumb_dest)
            except Exception as exc:
                logger.warning("Thumb failed: %s", exc)

            image_row = add_job_image(
                job_id,
                index=image_index,
                seed=seed,
                file_path=file_path,
                thumb_path=str(thumb_dest),
            )
            image_id = image_row["id"]
            completed += 1
            update_job_status(job_id, completed_count=completed)
            _publish(
                job_id,
                {
                    "type": "image_completed",
                    "job_id": job_id,
                    "image_index": image_index,
                    "image": image_row,
                    "progress": int((completed / request.image_count) * 100),
                },
            )

        if should_cancel():
            update_job_status(job_id, status="cancelled", finished=True)
            _publish(job_id, {"type": "cancelled", "job_id": job_id})
            return

        run_generation(
            request,
            on_step=on_step,
            on_image=on_image,
            should_cancel=should_cancel,
        )
        update_job_status(job_id, status="completed", finished=True)
        _publish(
            job_id,
            {"type": "done", "job_id": job_id, "progress": 100},
        )
        from .jobs import prune_job_history

        prune_job_history()
    except MemoryError as exc:
        suggested = suggest_smaller_preset(
            payload["model_id"], payload["size_preset_id"]
        )
        update_job_status(
            job_id,
            status="failed",
            error_message=str(exc),
            finished=True,
        )
        _publish(
            job_id,
            {
                "type": "failed",
                "job_id": job_id,
                "error": str(exc),
                "suggested_preset_id": suggested,
            },
        )
        _unload_pipeline()
    except RuntimeError as exc:
        if "cancelled" in str(exc):
            update_job_status(job_id, status="cancelled", finished=True)
            _publish(job_id, {"type": "cancelled", "job_id": job_id})
        else:
            update_job_status(
                job_id,
                status="failed",
                error_message=str(exc),
                finished=True,
            )
            _publish(
                job_id,
                {"type": "failed", "job_id": job_id, "error": str(exc)},
            )
    except Exception as exc:
        logger.exception("Job %s failed: %s", job_id, exc)
        update_job_status(
            job_id,
            status="failed",
            error_message=str(exc),
            finished=True,
        )
        _publish(
            job_id,
            {"type": "failed", "job_id": job_id, "error": str(exc)},
        )
    finally:
        _cancel_flags.pop(job_id, None)
        with _worker_lock:
            if _active_job_id == job_id:
                _active_job_id = None


def enqueue_job(payload: dict) -> dict:
    preflight = run_preflight_checks(force=True)
    if not preflight["critical_passed"]:
        raise ValueError("Critical preflight checks failed.")

    model_id = payload["model_id"]
    if model_id in catalog_by_id() and not is_model_downloaded(model_id):
        raise ValueError("Selected catalog model is not downloaded yet.")

    image_count = int(payload["image_count"])
    if image_count < 1 or image_count > MAX_IMAGES_PER_JOB:
        raise ValueError(f"image_count must be between 1 and {MAX_IMAGES_PER_JOB}")

    output_root, warning = ensure_output_directory()
    if warning:
        raise ValueError(warning)

    from .jobs import create_job_record

    job = create_job_record(payload, str(output_root))
    job_id = job["id"]

    update_last_form_values(
        model_id=payload["model_id"],
        size_preset_id=payload["size_preset_id"],
        steps=int(payload.get("steps") or 25),
    )

    def _start() -> None:
        global _active_job_id
        with _worker_lock:
            _active_job_id = job_id
        _process_job(job_id, payload)

    thread = threading.Thread(target=_start, name=f"gen-{job_id}", daemon=True)
    thread.start()
    return get_job(job_id)  # type: ignore[return-value]
