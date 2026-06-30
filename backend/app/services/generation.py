from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..config import DEFAULT_STEPS
from .models import catalog_by_id, get_compatible_presets, get_model_entry, resolve_model_path
from .gpu import detect_gpu, total_vram_gb

logger = logging.getLogger(__name__)

_pipeline_cache: dict[str, Any] = {"model_id": None, "pipeline": None}


@dataclass
class GenerationRequest:
    job_id: str
    prompt: str
    negative_prompt: str
    model_id: str
    width: int
    height: int
    steps: int
    seed: int | None
    image_count: int
    output_dir: Path
    size_preset_id: str


def _unload_pipeline() -> None:
    global _pipeline_cache
    pipeline = _pipeline_cache.get("pipeline")
    if pipeline is not None:
        try:
            del pipeline
        except Exception:
            pass
    _pipeline_cache = {"model_id": None, "pipeline": None}
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


def _apply_gpu_speedups() -> None:
    try:
        import torch

        if not torch.cuda.is_available():
            return
        props = torch.cuda.get_device_properties(0)
        if props.major >= 8:
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.benchmark = True
    except Exception as exc:
        logger.info("GPU speedup flags not applied: %s", exc)


def _load_pipeline(model_id: str, family: str, model_path: Path) -> Any:
    global _pipeline_cache
    if _pipeline_cache["model_id"] == model_id and _pipeline_cache["pipeline"] is not None:
        return _pipeline_cache["pipeline"]

    _unload_pipeline()
    import torch
    from diffusers import (
        DPMSolverMultistepScheduler,
        StableDiffusionPipeline,
        StableDiffusionXLPipeline,
    )

    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    common_kwargs: dict[str, Any] = {
        "torch_dtype": dtype,
        "safety_checker": None,
    }

    if family == "sdxl":
        pipe = StableDiffusionXLPipeline.from_pretrained(
            str(model_path),
            **common_kwargs,
        )
        if hasattr(pipe, "enable_vae_tiling"):
            pipe.enable_vae_tiling()
    else:
        pipe = StableDiffusionPipeline.from_pretrained(
            str(model_path),
            **common_kwargs,
        )

    pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)

    if torch.cuda.is_available():
        pipe = pipe.to("cuda")
        try:
            pipe.enable_attention_slicing()
        except Exception:
            pass

    _apply_gpu_speedups()

    # Warmup
    try:
        with torch.inference_mode():
            pipe(
                prompt="warmup",
                num_inference_steps=1,
                width=min(pipe.unet.config.sample_size * 8, 512) if family != "sdxl" else 512,
                height=min(pipe.unet.config.sample_size * 8, 512) if family != "sdxl" else 512,
                output_type="latent",
            )
    except Exception as exc:
        logger.info("Pipeline warmup skipped: %s", exc)

    _pipeline_cache = {"model_id": model_id, "pipeline": pipe}
    return pipe


def suggest_smaller_preset(model_id: str, current_preset_id: str) -> str | None:
    entry = get_model_entry(model_id) or catalog_by_id().get(model_id)
    if not entry:
        return None
    gpu = detect_gpu()
    effective = total_vram_gb(gpu)
    if effective is not None:
        effective = max(0.0, effective - 0.75)
    presets = get_compatible_presets(entry, effective)
    ordered = sorted(presets, key=lambda p: p["width"] * p["height"], reverse=True)
    ids = [p["id"] for p in ordered]
    if current_preset_id not in ids:
        return ordered[-1]["id"] if ordered else None
    idx = ids.index(current_preset_id)
    if idx + 1 < len(ids):
        return ids[idx + 1]
    return None


def run_generation(
    request: GenerationRequest,
    *,
    on_step,
    on_image,
    should_cancel,
) -> None:
    import torch
    from PIL import Image

    entry = get_model_entry(request.model_id) or catalog_by_id().get(request.model_id)
    if entry is None:
        raise ValueError(f"Unknown model: {request.model_id}")

    model_path = resolve_model_path(request.model_id)
    if model_path is None or not model_path.exists():
        raise FileNotFoundError(f"Model files not found for {request.model_id}")

    family = entry.get("family", "sd15")
    pipe = _load_pipeline(request.model_id, family, model_path)
    request.output_dir.mkdir(parents=True, exist_ok=True)

    base_seed = request.seed if request.seed is not None else random.randint(0, 2**32 - 1)
    completed_images: list[dict[str, Any]] = []

    prompt_embeds = None
    negative_prompt_embeds = None

    with torch.inference_mode():
        if family == "sdxl":
            enc = pipe.encode_prompt(
                prompt=request.prompt,
                prompt_2=request.prompt,
                device=pipe.device,
                num_images_per_prompt=1,
                do_classifier_free_guidance=True,
                negative_prompt=request.negative_prompt or None,
                negative_prompt_2=request.negative_prompt or None,
            )
            prompt_embeds = enc[0]
            negative_prompt_embeds = enc[1]
        else:
            enc = pipe.encode_prompt(
                prompt=request.prompt,
                device=pipe.device,
                num_images_per_prompt=1,
                do_classifier_free_guidance=True,
                negative_prompt=request.negative_prompt or None,
            )
            prompt_embeds = enc[0]
            negative_prompt_embeds = enc[1]

        for image_index in range(1, request.image_count + 1):
            if should_cancel():
                raise RuntimeError("cancelled")

            seed = base_seed + (image_index - 1)
            generator = torch.Generator(device=pipe.device).manual_seed(seed)

            def _callback(pipe_obj, step_index, timestep, callback_kwargs):
                if should_cancel():
                    raise RuntimeError("cancelled")
                on_step(step_index + 1, request.steps, image_index)
                return callback_kwargs

            try:
                result = pipe(
                    prompt_embeds=prompt_embeds,
                    negative_prompt_embeds=negative_prompt_embeds,
                    width=request.width,
                    height=request.height,
                    num_inference_steps=request.steps,
                    generator=generator,
                    callback_on_step_end=_callback,
                    callback_on_step_end_tensor_inputs=["latents"],
                )
                image: Image.Image = result.images[0]
            except RuntimeError as exc:
                if "cancelled" in str(exc):
                    raise
                if "out of memory" in str(exc).lower():
                    _unload_pipeline()
                    raise MemoryError(
                        f"CUDA out of memory at preset {request.size_preset_id}"
                    ) from exc
                raise

            file_name = f"{request.job_id}_{image_index}_{seed}.png"
            file_path = request.output_dir / file_name
            image.save(file_path)
            completed_images.append(
                {
                    "index": image_index,
                    "seed": seed,
                    "file_path": str(file_path),
                }
            )
            on_image(image_index, seed, str(file_path))

    from .jobs import write_job_json

    write_job_json(
        request.output_dir,
        {
            "id": request.job_id,
            "prompt": request.prompt,
            "negative_prompt": request.negative_prompt,
            "model_id": request.model_id,
            "size_preset_id": request.size_preset_id,
            "width": request.width,
            "height": request.height,
            "steps": request.steps,
            "seed": base_seed,
            "image_count": request.image_count,
        },
        [{"index": i["index"], "seed": i["seed"], "file_path": i["file_path"]} for i in completed_images],
    )
