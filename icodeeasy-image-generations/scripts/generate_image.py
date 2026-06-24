#!/usr/bin/env python3
"""Call iCodeEasy's OpenAI-compatible image endpoints."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


BASE_URL = "https://jp.icodeeasy.cc"
MODEL = "gpt-image-2"
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
            return response.status, json.loads(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed: dict[str, Any] = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"error": {"message": body or str(exc)}}
        raise UserError(f"HTTP {exc.code}: {json.dumps(parsed, ensure_ascii=False)}") from None
    except urllib.error.URLError as exc:
        raise UserError(f"Network error: {exc.reason}") from None
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
    directory.mkdir(parents=True, exist_ok=True)
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
        with urllib.request.urlopen(request, timeout=timeout) as response:
            target.write_bytes(response.read())
        paths.append(str(target))
    return paths


def normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def image_endpoint_url(base_url: str, path: str, async_mode: bool) -> str:
    url = normalize_base_url(base_url) + path
    if async_mode:
        url += "?async=1"
    return url


def task_url(base_url: str, task_id: str) -> str:
    return normalize_base_url(base_url) + TASK_PATH_PREFIX + urllib.parse.quote(task_id)


def emit(args: argparse.Namespace, result: dict[str, Any]) -> None:
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if not result.get("ok"):
        print(result.get("summary", "Request failed"), file=sys.stderr)
        return

    print(result.get("summary", "OK"))
    for url in result.get("urls", []):
        print(url)
    for path in result.get("downloads", []):
        print(path)
    if result.get("task_id"):
        print(f"task_id: {result['task_id']}")


def collect_image_urls(args: argparse.Namespace) -> list[str]:
    image_urls = list(args.image_url or [])
    image_urls.extend(image_file_to_data_url(path) for path in args.image_file or [])
    if len(image_urls) > 16:
        raise UserError("image_urls supports at most 16 reference images.")
    return image_urls


def build_payload(args: argparse.Namespace, *, require_reference: bool) -> dict[str, Any]:
    image_urls = collect_image_urls(args)
    if require_reference and not image_urls:
        raise UserError("Edit requests require at least one --image-url or --image-file.")
    payload: dict[str, Any] = {
        "model": MODEL,
        "prompt": args.prompt,
        "n": args.n,
        "resolution": args.resolution,
        "quality": args.quality,
    }
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
    deadline = time.time() + max_wait
    last_status = 0
    last_response: dict[str, Any] = {}

    while True:
        last_status, last_response = request_json(
            "GET", task_url(base_url, task_id), api_key, timeout=timeout
        )
        status_text = last_response.get("status")
        if not wait or status_text in {"completed", "failed"}:
            return last_status, last_response
        if time.time() >= deadline:
            return last_status, last_response
        time.sleep(interval)


def command_submit(args: argparse.Namespace) -> int:
    path = EDITS_PATH if args.command == "edit" else GENERATIONS_PATH
    payload = build_payload(args, require_reference=args.command == "edit")
    api_key, key_env = resolve_api_key()
    url = image_endpoint_url(args.base_url, path, args.async_mode)

    if args.dry_run:
        safe_payload = dict(payload)
        if "image_urls" in safe_payload:
            safe_payload["image_urls"] = [
                value if isinstance(value, str) and value.startswith("https://") else "<data-url>"
                for value in safe_payload["image_urls"]
            ]
        emit(
            args,
            {
                "ok": True,
                "summary": "Dry run only. No network request was sent.",
                "method": "POST",
                "url": url,
                "key_env": key_env,
                "payload": safe_payload,
            },
        )
        return 0

    http_status, response = request_json("POST", url, api_key, payload=payload, timeout=args.timeout)
    task_id = response.get("task_id") if isinstance(response.get("task_id"), str) else None

    waited_for_completion = False
    if args.async_mode and args.wait and task_id:
        waited_for_completion = True
        http_status, response = poll_task(
            task_id=task_id,
            api_key=api_key,
            base_url=args.base_url,
            timeout=args.timeout,
            wait=True,
            interval=args.poll_interval,
            max_wait=args.max_wait,
        )

    urls = collect_result_urls(response)
    downloads = download_urls(urls, args.download_dir, args.timeout)
    status_text = response.get("status")
    ok = status_text != "failed" and not (
        waited_for_completion and status_text != "completed"
    )
    summary = f"HTTP {http_status}; endpoint={path}; model={MODEL}; key_env={key_env}"
    if status_text:
        summary += f"; status={status_text}"
    if waited_for_completion and status_text != "completed":
        summary += "; task did not complete before max wait"
    emit(
        args,
        {
            "ok": ok,
            "summary": summary,
            "http_status": http_status,
            "key_env": key_env,
            "task_id": task_id or response.get("task_id"),
            "urls": urls,
            "downloads": downloads,
            "response": response,
        },
    )
    return 0 if ok else 1


def command_poll(args: argparse.Namespace) -> int:
    api_key, key_env = resolve_api_key()
    http_status, response = poll_task(
        task_id=args.task_id,
        api_key=api_key,
        base_url=args.base_url,
        timeout=args.timeout,
        wait=args.wait,
        interval=args.interval,
        max_wait=args.max_wait,
    )
    urls = collect_result_urls(response)
    downloads = download_urls(urls, args.download_dir, args.timeout)
    status_text = response.get("status")
    ok = status_text != "failed" and not (args.wait and status_text != "completed")
    summary = f"HTTP {http_status}; key_env={key_env}; status={status_text}"
    if args.wait and status_text != "completed":
        summary += "; task did not complete before max wait"
    emit(
        args,
        {
            "ok": ok,
            "summary": summary,
            "http_status": http_status,
            "key_env": key_env,
            "task_id": args.task_id,
            "urls": urls,
            "downloads": downloads,
            "response": response,
        },
    )
    return 0 if ok else 1


def add_common_network_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--base-url", default=BASE_URL, help=f"API host, default: {BASE_URL}")
    parser.add_argument("--timeout", type=int, default=220, help="HTTP timeout seconds")
    parser.add_argument("--json", action="store_true", help="print structured JSON output")


def add_submit_args(parser: argparse.ArgumentParser, *, prompt_help: str) -> None:
    add_common_network_args(parser)
    parser.add_argument("--prompt", required=True, help=prompt_help)
    parser.add_argument("--n", type=positive_int, default=1, help="number of images")
    parser.add_argument("--resolution", choices=["1k", "2k"], default="1k")
    parser.add_argument("--quality", choices=["low", "medium", "high", "auto"], default="medium")
    parser.add_argument(
        "--image-url",
        action="append",
        type=validate_ref,
        help="reference image as https:// URL or data:image data URL; repeatable",
    )
    parser.add_argument(
        "--image-file",
        action="append",
        help="local reference image file encoded into image_urls; repeatable",
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
