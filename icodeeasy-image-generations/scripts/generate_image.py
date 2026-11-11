#!/usr/bin/env python3
"""Call iCodeEasy's OpenAI-compatible image endpoints."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import shlex
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


BASE_URL = "https://jp.icodeeasy.cc"
MODEL = "gpt-image-2"
GPT_MODELS = (MODEL, "gpt-image-2.5-flare", "gpt-image-2.5-sunburst", "gpt-image-2.6-flare", "gpt-image-2.6-sunburst")
SEEDREAM_LITE = "doubao-seedream-5-0-lite"
# The first tier is the relay's default for each model.
SEEDREAM_TIERS = {
    "seedream-5-5": ("2k", "1k", "1.5k"),
    "seedream-5-0-flash": ("1k", "1.5k", "2k"),
    "seedream-5-0-pro": ("1k", "1.5k", "2k"),
    "seedream-4-5": ("2k", "4k"),
    "seedream-4-0": ("2k", "1k", "4k"),
    SEEDREAM_LITE: ("2k", "3k"),
}
SEEDREAM_LITE_RATIOS = ("1:1", "4:3", "3:4", "16:9", "9:16", "3:2", "2:3", "21:9")
FLUX_2_MODELS = ("flux-2-pro", "flux-2-max", "flux-2-flex")
FLUX_3_MODELS = ("flux-3-image", "flux-3-image-klein")
FLUX_3_RATIOS = ("1:1", "9:16", "16:9", "2:3", "3:2", "4:5", "5:4")
FLUX_3_TIERS = ("1k", "768sq", "1.5k", "2k", "4k")
GPT_TIERS = ("1k", "2k", "4k")
MODELS = (*GPT_MODELS, *SEEDREAM_TIERS, *FLUX_2_MODELS, *FLUX_3_MODELS)
ASPECT_RATIOS = ("auto", "1:1", "3:2", "2:3", "16:9", "9:16", "4:3", "3:4", "4:5", "5:4")
GENERATIONS_PATH = "/v1/images/generations"
EDITS_PATH = "/v1/images/edits"
TASK_PATH_PREFIX = "/v1/images/tasks/"
KEY_ENV_ORDER = ("OPENAI_API_KEY", "ANTHROPIC_AUTH_TOKEN")


class UserError(Exception):
    """Input or environment error that should be shown without a traceback."""


def resolve_api_key() -> tuple[str, str]:
    for env_name in KEY_ENV_ORDER:
        value = os.environ.get(env_name)
        if value:
            return value, env_name
    joined = " or ".join(KEY_ENV_ORDER)
    raise UserError(f"Missing API key. Set {joined}.")


def validate_ref(value: str) -> str:
    if value.startswith("https://"):
        return value
    if value.startswith("data:image/") and ";base64," in value:
        return value
    raise argparse.ArgumentTypeError(
        "reference images must be https:// URLs or data:image/...;base64,... values"
    )


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be an integer") from None
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def image_file_to_data_url(path_text: str) -> str:
    path = Path(path_text).expanduser()
    if not path.is_file():
        raise UserError(f"Reference image file not found: {path}")
    mime_type = mimetypes.guess_type(path.name)[0] or "image/png"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{data}"


def request_json(
    method: str,
    url: str,
    api_key: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout: int,
) -> tuple[int, dict[str, Any]]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Authorization": f"Bearer {api_key}"}
    if payload is not None:
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            parsed = json.loads(body)
            if not isinstance(parsed, dict):
                raise UserError("Response JSON must be an object.")
            return response.status, parsed
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed: dict[str, Any] = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"error": {"message": body or str(exc)}}
        raise UserError(f"HTTP {exc.code}: {json.dumps(parsed, ensure_ascii=False)}") from None
    except urllib.error.URLError as exc:
        raise UserError(f"Network error: {exc.reason}") from None
    except (TimeoutError, OSError) as exc:
        raise UserError(f"Network error: {exc}") from None
    except json.JSONDecodeError as exc:
        raise UserError(f"Response was not valid JSON: {exc}") from None


def collect_result_urls(response: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for item in response.get("data") or []:
        if isinstance(item, dict) and isinstance(item.get("url"), str):
            urls.append(item["url"])
    result_url = response.get("result_url")
    if isinstance(result_url, str):
        urls.append(result_url)
    return urls


def download_urls(urls: list[str], output_dir: str | None, timeout: int) -> list[str]:
    if not output_dir:
        return []
    directory = Path(output_dir).expanduser()
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise UserError(f"Cannot create download directory: {exc}") from None
    paths: list[str] = []
    for index, url in enumerate(urls, start=1):
        parsed = urllib.parse.urlparse(url)
        suffix = Path(parsed.path).suffix or ".png"
        name = Path(parsed.path).name or f"image-{index}{suffix}"
        if not Path(name).suffix:
            name = f"{name}{suffix}"
        target = directory / name
        if target.exists():
            target = directory / f"{target.stem}-{int(time.time())}-{index}{target.suffix}"
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; Codex image downloader)"},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                target.write_bytes(response.read())
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise UserError(f"Image download failed: {exc}") from None
        paths.append(str(target))
    return paths


def normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def image_endpoint_url(base_url: str, path: str, async_mode: bool) -> str:
    url = normalize_base_url(base_url) + path
    return url + ("?async=1" if async_mode else "?sync=1")


def task_url(base_url: str, task_id: str) -> str:
    return normalize_base_url(base_url) + TASK_PATH_PREFIX + urllib.parse.quote(task_id, safe="")


def redact_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: redact_secrets(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    if isinstance(value, str):
        for env_name in KEY_ENV_ORDER:
            secret = os.environ.get(env_name)
            if secret:
                value = value.replace(secret, "[REDACTED]")
    return value


def emit(args: argparse.Namespace, result: dict[str, Any]) -> None:
    result = redact_secrets(result)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if not result.get("ok"):
        print(result.get("summary", "Request failed"), file=sys.stderr)
    else:
        print(result.get("summary", "OK"))
    for url in result.get("urls", []):
        print(url)
    for path in result.get("downloads", []):
        print(path)
    if result.get("task_id"):
        print(f"task_id: {result['task_id']}")
    if result.get("resume_command"):
        print("Resume the same task:", shlex.join(result["resume_command"]))


def collect_image_urls(args: argparse.Namespace) -> list[str]:
    image_urls = list(args.image_url or [])
    image_files = args.image_file or []
    limit = 10 if args.model == "seedream-5-5" else 8
    if len(image_urls) + len(image_files) > limit:
        raise UserError(f"{args.model} supports at most {limit} reference images.")
    image_urls.extend(image_file_to_data_url(path) for path in image_files)
    return image_urls


def image_tier(args: argparse.Namespace, tiers: tuple[str, ...]) -> str:
    tier = args.resolution or tiers[0]
    if tier not in tiers:
        raise UserError(f"Unsupported resolution for {args.model}. Use {', '.join(tiers)}.")
    return tier if tier == "768sq" else tier.upper()


def build_generation_only_payload(args: argparse.Namespace, image_urls: list[str]) -> dict[str, Any]:
    if args.quality is not None:
        raise UserError(f"--quality is not supported for {args.model}.")

    payload: dict[str, Any] = {"model": args.model, "prompt": args.prompt, "n": 1}
    if image_urls:
        payload["image_input"] = image_urls
    if args.seed is not None:
        if args.model not in FLUX_2_MODELS and args.model != "flux-3-image-klein":
            raise UserError(f"--seed is not supported for {args.model}.")
        if not 0 <= args.seed <= 4_294_967_295:
            raise UserError("--seed must be from 0 to 4294967295.")
        payload["seed"] = args.seed

    if args.model in FLUX_2_MODELS:
        if args.resolution is not None or args.aspect_ratio is not None:
            raise UserError(f"Use --size WIDTHxHEIGHT for {args.model}.")
        size = args.size or "1024x1024"
        match = re.fullmatch(r"([0-9]{1,5})x([0-9]{1,5})", size, re.IGNORECASE)
        if match is None:
            raise UserError("--size must be WIDTHxHEIGHT, with at least 64 pixels per side and at most 4 MP.")
        width, height = map(int, match.groups())
        if min(width, height) < 64 or width * height > 4 * 1024 * 1024:
            raise UserError("--size must have at least 64 pixels per side and at most 4 MP.")
        payload["size"] = f"{width}x{height}"
        return payload

    if args.size is not None:
        raise UserError(f"Use --resolution and --aspect-ratio instead of --size for {args.model}.")
    if args.model in SEEDREAM_TIERS:
        tiers = SEEDREAM_TIERS[args.model]
        ratios = SEEDREAM_LITE_RATIOS
        if args.model != SEEDREAM_LITE:
            ratios += ("2:1", "1:2")
        if args.model.startswith("seedream-4-"):
            ratios += ("9:21",)
        if args.model == "seedream-4-0" and len(args.prompt) > 1000:
            raise UserError("Seedream 4.0 prompt must not exceed 1000 characters.")
    else:
        tiers, ratios = FLUX_3_TIERS, FLUX_3_RATIOS
    ratio = args.aspect_ratio or "1:1"
    if ratio not in ratios:
        raise UserError(f"Unsupported aspect ratio for {args.model}. Use {', '.join(ratios)}.")
    payload["aspect_ratio"] = ratio
    payload["image_size"] = image_tier(args, tiers)
    return payload


def build_payload(args: argparse.Namespace, *, require_reference: bool) -> dict[str, Any]:
    generation_only = args.model not in GPT_MODELS
    if generation_only and require_reference:
        raise UserError(f"{args.model} uses generate with --image-url or --image-file for image-to-image requests.")
    if args.model != "gpt-image-2" and args.n != 1:
        raise UserError(f"{args.model} supports one image per request. Use --n 1.")
    image_urls = collect_image_urls(args)
    if generation_only:
        return build_generation_only_payload(args, image_urls)
    if args.size is not None or args.seed is not None:
        raise UserError(f"--size and --seed are not supported for {args.model}.")
    tier = image_tier(args, GPT_TIERS)
    if args.model.startswith("gpt-image-2.6-") and tier in ("2K", "4K") and any(
        url.startswith("data:") and url.partition(";")[0].lower() not in (
            "data:image/png", "data:image/jpeg", "data:image/jpg", "data:image/webp"
        )
        for url in image_urls
    ):
        raise UserError("Use PNG, JPEG, or WebP reference images with GPT Image 2.6 at 2K or 4K.")
    if require_reference and not image_urls:
        raise UserError("Edit requests require at least one --image-url or --image-file.")
    if args.aspect_ratio:
        ratios = ASPECT_RATIOS + (("21:9",) if args.model.startswith("gpt-image-2.5-") else ())
        if args.aspect_ratio not in ratios:
            raise UserError(f"Unsupported aspect ratio for {args.model}.")
    payload: dict[str, Any] = {
        "model": args.model,
        "prompt": args.prompt,
        "n": args.n,
        "image_size": tier,
        "quality": args.quality or ("medium" if args.model == "gpt-image-2" else "auto"),
    }
    if args.aspect_ratio:
        payload["aspect_ratio"] = args.aspect_ratio
    if image_urls:
        payload["image_urls"] = image_urls
    return payload


def poll_task(
    *,
    task_id: str,
    api_key: str,
    base_url: str,
    timeout: int,
    wait: bool,
    interval: float,
    max_wait: float,
) -> tuple[int, dict[str, Any]]:
    deadline = time.monotonic() + max_wait
    last_status = 0
    last_response: dict[str, Any] = {}

    while True:
        last_status, last_response = request_json(
            "GET", task_url(base_url, task_id), api_key, timeout=timeout
        )
        status_text = last_response.get("status")
        if not wait or status_text not in {"pending", "submitted", "processing", "queued", "running"}:
            return last_status, last_response
        if time.monotonic() >= deadline:
            return last_status, last_response
        time.sleep(interval)


def emit_recovery(
    args: argparse.Namespace,
    error: UserError,
    *,
    stage: str,
    task_id: str | None,
    urls: list[str] | None = None,
    response: dict[str, Any] | None = None,
) -> int:
    result: dict[str, Any] = {
        "ok": False,
        "summary": f"{stage.capitalize()} failed: {error}",
        "stage": stage,
        "task_id": task_id,
        "urls": urls or [],
        "response": response or {},
    }
    if task_id:
        result["resume_command"] = [
            "python3", str(Path(__file__).resolve()), "poll", task_id,
            "--base-url", args.base_url, "--wait",
        ]
        if args.download_dir:
            result["resume_command"].extend(["--download-dir", args.download_dir])
    emit(args, result)
    return 1


def emit_response(
    args: argparse.Namespace,
    *,
    http_status: int,
    response: dict[str, Any],
    task_id: str | None,
    key_env: str,
    waited: bool,
) -> int:
    urls = collect_result_urls(response)
    try:
        downloads = download_urls(urls, args.download_dir, args.timeout)
    except UserError as exc:
        return emit_recovery(args, exc, stage="download", task_id=task_id, urls=urls, response=response)
    status_text = response.get("status")
    ok = status_text not in {"failed", "error", "cancelled", "canceled"}
    ok = ok and (not waited or status_text == "completed") and bool(urls or task_id)
    if status_text == "completed" and not urls:
        ok = False
    summary = f"HTTP {http_status}; key_env={key_env}"
    model = getattr(args, "model", None)
    if model:
        summary += f"; model={model}"
    if status_text:
        summary += f"; status={status_text}"
    if waited and status_text != "completed":
        summary += "; task did not complete; resume with its task ID"
    emit(args, {
        "ok": ok,
        "summary": summary,
        "model": model,
        "http_status": http_status,
        "key_env": key_env,
        "task_id": task_id,
        "urls": urls,
        "downloads": downloads,
        "response": response,
    })
    return 0 if ok else 1


def command_submit(args: argparse.Namespace) -> int:
    path = EDITS_PATH if args.command == "edit" else GENERATIONS_PATH
    payload = build_payload(args, require_reference=args.command == "edit")
    url = image_endpoint_url(args.base_url, path, args.async_mode)

    if args.dry_run:
        safe_payload = dict(payload)
        for field in ("image_urls", "image_input"):
            if field in safe_payload:
                safe_payload[field] = [
                    value if value.startswith("https://") else "<data-url>"
                    for value in safe_payload[field]
                ]
        emit(args, {
            "ok": True,
            "summary": "Dry run only. No network request was sent.",
            "method": "POST",
            "url": url,
            "payload": safe_payload,
        })
        return 0

    api_key, key_env = resolve_api_key()
    http_status, response = request_json("POST", url, api_key, payload=payload, timeout=args.timeout)
    task_id = response.get("task_id") or response.get("id")
    if not isinstance(task_id, str):
        task_id = None
    if http_status == 202 and not task_id:
        raise UserError("Task accepted without a task ID. Check account logs before submitting again.")

    waited = bool(task_id and (args.wait or not args.async_mode) and not collect_result_urls(response))
    if waited:
        try:
            http_status, response = poll_task(
                task_id=task_id,
                api_key=api_key,
                base_url=args.base_url,
                timeout=args.timeout,
                wait=True,
                interval=args.poll_interval,
                max_wait=args.max_wait,
            )
        except UserError as exc:
            return emit_recovery(args, exc, stage="poll", task_id=task_id)

    return emit_response(args, http_status=http_status, response=response, task_id=task_id, key_env=key_env, waited=waited)


def command_poll(args: argparse.Namespace) -> int:
    api_key, key_env = resolve_api_key()
    try:
        http_status, response = poll_task(
            task_id=args.task_id,
            api_key=api_key,
            base_url=args.base_url,
            timeout=args.timeout,
            wait=args.wait,
            interval=args.interval,
            max_wait=args.max_wait,
        )
    except UserError as exc:
        return emit_recovery(args, exc, stage="poll", task_id=args.task_id)
    return emit_response(args, http_status=http_status, response=response, task_id=args.task_id, key_env=key_env, waited=args.wait)


def add_common_network_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--base-url", default=BASE_URL, help=f"API host, default: {BASE_URL}")
    parser.add_argument("--timeout", type=int, default=220, help="HTTP timeout seconds")
    parser.add_argument("--json", action="store_true", help="print structured JSON output")


def add_submit_args(parser: argparse.ArgumentParser, *, prompt_help: str) -> None:
    add_common_network_args(parser)
    parser.add_argument("--prompt", required=True, help=prompt_help)
    parser.add_argument("--model", choices=MODELS, default=MODEL, help="image model")
    parser.add_argument("--n", type=positive_int, default=1, help="number of images; only GPT Image 2 accepts more than one")
    parser.add_argument(
        "--resolution", type=str.lower, choices=("768sq", "1k", "1.5k", "2k", "3k", "4k"),
        help="resolution tier for GPT Image, Seedream, or FLUX 3; defaults depend on model",
    )
    parser.add_argument("--size", help="FLUX 2 pixel dimensions, such as 1920x1080; default 1024x1024")
    parser.add_argument("--seed", type=int, help="optional seed for FLUX 2 and FLUX 3 Image Klein")
    parser.add_argument("--quality", choices=["low", "medium", "high", "auto"], help="GPT Image only; defaults to medium for 2, auto for 2.5/2.6")
    parser.add_argument("--aspect-ratio", help="optional image ratio, such as 1:1 or 16:9")
    parser.add_argument(
        "--image-url",
        action="append",
        type=validate_ref,
        help="reference image as https:// URL or data:image data URL; repeatable",
    )
    parser.add_argument(
        "--image-file",
        action="append",
        help="local reference image file encoded as an image data URL; repeatable",
    )
    parser.add_argument("--async", dest="async_mode", action="store_true", help="submit async task")
    parser.add_argument("--wait", action="store_true", help="wait for async task completion")
    parser.add_argument("--poll-interval", type=float, default=5.0, help="async poll interval seconds")
    parser.add_argument("--max-wait", type=float, default=300.0, help="max async wait seconds")
    parser.add_argument("--download-dir", help="download completed image URLs into this directory")
    parser.add_argument("--dry-run", action="store_true", help="print request without sending it")
    parser.set_defaults(func=command_submit)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate or image-to-image edit pictures through iCodeEasy image endpoints."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="submit a generations request")
    add_submit_args(generate, prompt_help="image prompt")

    edit = subparsers.add_parser("edit", help="submit an edits request")
    add_submit_args(edit, prompt_help="edit prompt")

    poll = subparsers.add_parser("poll", help="poll an async image task")
    add_common_network_args(poll)
    poll.add_argument("task_id", help="task id returned by async generate")
    poll.add_argument("--wait", action="store_true", help="poll until completed or failed")
    poll.add_argument("--interval", type=float, default=5.0, help="poll interval seconds")
    poll.add_argument("--max-wait", type=float, default=300.0, help="max wait seconds")
    poll.add_argument("--download-dir", help="download completed image URLs into this directory")
    poll.set_defaults(func=command_poll)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except UserError as exc:
        result = {"ok": False, "summary": str(exc)}
        emit(args, result)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
