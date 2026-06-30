from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .api.sse import router as sse_router
from .config import FRONTEND_DIST, HOST, PORT, ensure_directories
from .db.database import init_database, mark_interrupted_jobs
from .services.downloads import download_catalog_model
from .services.logging_config import prune_old_logs, setup_logging
from .services.jobs import (
    cancel_job,
    delete_job,
    get_job,
    get_job_image,
    list_jobs,
    prune_job_history,
    recent_images,
)
from .services.models import get_models_list, refresh_models
from .services.preflight import get_cached_preflight, invalidate_preflight_cache, run_preflight_checks
from .services.prompts import (
    create_saved_prompt,
    delete_saved_prompt,
    get_saved_prompt,
    list_saved_prompts,
    load_templates,
    update_saved_prompt,
)
from .services.settings import (
    browse_output_directory,
    ensure_output_directory,
    load_settings,
    save_settings,
    validate_output_directory,
)
from .services.worker import enqueue_job, request_cancel

logger = logging.getLogger(__name__)


class SettingsUpdate(BaseModel):
    output_directory: str | None = None
    last_model_id: str | None = None
    last_size_preset_id: str | None = None
    last_steps: int | None = None
    history_retention_days: int | None = None
    history_retention_max_jobs: int | None = None
    log_retention_days: int | None = None


class PathRequest(BaseModel):
    path: str


class CreateJobRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    model_id: str
    size_preset_id: str
    width: int
    height: int
    steps: int = 25
    seed: int | None = None
    image_count: int = Field(default=1, ge=1, le=10)


class SavedPromptCreate(BaseModel):
    name: str
    prompt: str
    negative_prompt: str = ""
    tags: list[str] = Field(default_factory=list)
    is_favorite: bool = False
    source_template_id: str | None = None
    notes: str | None = None


class SavedPromptUpdate(BaseModel):
    name: str | None = None
    prompt: str | None = None
    negative_prompt: str | None = None
    tags: list[str] | None = None
    is_favorite: bool | None = None
    source_template_id: str | None = None
    notes: str | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_directories()
    settings = load_settings()
    setup_logging(int(settings.get("log_retention_days", 30)))
    init_database()
    interrupted = mark_interrupted_jobs()
    if interrupted:
        logger.info("Marked %s jobs as interrupted", interrupted)
    prune_job_history()
    prune_old_logs(int(settings.get("log_retention_days", 30)))
    run_preflight_checks(force=True)
    logger.info("Backend ready on %s:%s", HOST, PORT)
    yield


app = FastAPI(title="OnPrem Image Generator", lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=500)
app.include_router(sse_router, prefix="/api")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/system/preflight")
def get_preflight() -> dict[str, Any]:
    return run_preflight_checks(force=True)


@app.get("/api/system/preflight/status")
def get_preflight_status() -> dict[str, Any]:
    return get_cached_preflight()


@app.post("/api/system/preflight/rerun")
def rerun_preflight() -> dict[str, Any]:
    invalidate_preflight_cache()
    return run_preflight_checks(force=True)


@app.get("/api/settings")
def get_settings() -> dict[str, Any]:
    settings = load_settings()
    ensure_output_directory(settings)
    return settings


@app.put("/api/settings")
def put_settings(body: SettingsUpdate) -> dict[str, Any]:
    patch = body.model_dump(exclude_none=True)
    if "output_directory" in patch:
        valid, message = validate_output_directory(patch["output_directory"])
        if not valid:
            raise HTTPException(status_code=400, detail=message)
    return save_settings(patch)


@app.post("/api/settings/output-directory/validate")
def validate_output_path(body: PathRequest) -> dict[str, Any]:
    valid, message = validate_output_directory(body.path)
    return {"valid": valid, "message": message}


@app.post("/api/settings/output-directory/browse")
def browse_output_path() -> dict[str, str | None]:
    return {"path": browse_output_directory()}


@app.get("/api/models")
def api_get_models() -> dict[str, Any]:
    return get_models_list()


@app.post("/api/models/refresh")
def api_refresh_models() -> dict[str, Any]:
    return refresh_models()


@app.post("/api/models/{model_id}/download")
def api_download_model(model_id: str) -> dict[str, Any]:
    try:
        return download_catalog_model(model_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Download failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/prompts/templates")
def api_templates() -> dict[str, Any]:
    return {"templates": load_templates()}


@app.get("/api/prompts/saved")
def api_saved_prompts(
    q: str | None = None,
    tag: str | None = None,
    favorite: bool = False,
) -> dict[str, Any]:
    prompts = list_saved_prompts(q=q, tag=tag, favorite=favorite or None)
    return {"prompts": prompts}


@app.post("/api/prompts/saved")
def api_create_saved_prompt(body: SavedPromptCreate) -> dict[str, Any]:
    return create_saved_prompt(body.model_dump())


@app.get("/api/prompts/saved/{prompt_id}")
def api_get_saved_prompt(prompt_id: str) -> dict[str, Any]:
    prompt = get_saved_prompt(prompt_id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt


@app.put("/api/prompts/saved/{prompt_id}")
def api_update_saved_prompt(prompt_id: str, body: SavedPromptUpdate) -> dict[str, Any]:
    updated = update_saved_prompt(prompt_id, body.model_dump(exclude_none=True))
    if updated is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return updated


@app.delete("/api/prompts/saved/{prompt_id}", status_code=204)
def api_delete_saved_prompt(prompt_id: str) -> None:
    delete_saved_prompt(prompt_id)


@app.get("/api/jobs")
def api_list_jobs(
    status: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    return list_jobs(status=status, limit=limit, offset=offset)


@app.get("/api/jobs/recent-images")
def api_recent_images(limit: int = Query(default=50, ge=1, le=200)) -> dict[str, Any]:
    return {"images": recent_images(limit)}


@app.get("/api/jobs/{job_id}")
def api_get_job(job_id: str) -> dict[str, Any]:
    job = get_job(job_id, include_images=True)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.post("/api/jobs")
def api_create_job(body: CreateJobRequest) -> dict[str, Any]:
    try:
        return enqueue_job(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/jobs/{job_id}/cancel")
def api_cancel_job(job_id: str) -> dict[str, Any]:
    request_cancel(job_id)
    job = cancel_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.delete("/api/jobs/{job_id}", status_code=204)
def api_delete_job(job_id: str, delete_files: bool = False) -> None:
    if not delete_job(job_id, delete_files=delete_files):
        raise HTTPException(status_code=404, detail="Job not found")


@app.get("/api/images/{image_id}")
def api_get_image(image_id: str, download: bool = False) -> FileResponse:
    image = get_job_image(image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")
    path = Path(image["file_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="Image file missing")
    filename = path.name if download else None
    return FileResponse(path, media_type="image/png", filename=filename)


@app.get("/api/thumbs/{image_id}")
def api_get_thumb(image_id: str) -> FileResponse:
    image = get_job_image(image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    thumb = image.get("thumb_path")
    if thumb and Path(thumb).exists():
        return FileResponse(thumb, media_type="image/webp")
    source = Path(image["file_path"])
    if source.exists():
        return FileResponse(source, media_type="image/png")
    raise HTTPException(status_code=404, detail="Thumbnail not found")


def _mount_frontend() -> None:
    if not FRONTEND_DIST.exists():
        logger.warning("Frontend dist not found at %s", FRONTEND_DIST)
        return

    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount(
            "/assets",
            StaticFiles(directory=assets_dir),
            name="assets",
        )

    favicon = FRONTEND_DIST / "favicon.svg"
    if favicon.exists():

        @app.get("/favicon.svg")
        async def favicon_file() -> FileResponse:
            return FileResponse(favicon)

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str) -> FileResponse:
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        index = FRONTEND_DIST / "index.html"
        if not index.exists():
            raise HTTPException(status_code=404)
        return FileResponse(index)


_mount_frontend()


def main() -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
