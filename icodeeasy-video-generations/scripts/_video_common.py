#!/usr/bin/env python3
"""Shared, model-independent primitives for iCodeEasy video commands."""

from __future__ import annotations

import argparse
import http.client
import ipaddress
import json
import math
import os
import re
import secrets
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping


DEFAULT_BASE_URL = "https://api.icodeeasy.cc"
OFFICIAL_HOSTS = frozenset(
    {"api.icodeeasy.cc", "jp.icodeeasy.cc", "sg.icodeeasy.cc"}
)
KEY_ENV_ORDER = ("OPENAI_API_KEY", "ANTHROPIC_AUTH_TOKEN")
MAX_IDEMPOTENCY_KEY_LENGTH = 128
MAX_DOWNLOAD_REDIRECTS = 1
TASK_STATUSES_IN_PROGRESS = frozenset({"queued", "running"})
TASK_STATUSES_TERMINAL = frozenset({"succeeded", "failed"})
LOCAL_REFERENCE_HOSTS = frozenset(
    {"localhost", "localhost.localdomain", "ip6-localhost", "ip6-loopback"}
)
LOCAL_REFERENCE_HOST_SUFFIXES = (
    ".localhost",
    ".local",
    ".localdomain",
    ".internal",
    ".lan",
    ".home",
    ".corp",
)


class UserError(Exception):
    """Invalid input or environment state suitable for a concise CLI error."""


class ProtocolError(Exception):
    """A network, HTTP, or response error from exactly one API request."""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        error_code: str | None = None,
        response: Any = None,
        uncertain: bool = False,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.error_code = error_code
        self.response = response
        self.uncertain = uncertain


StandardValidation = Callable[[argparse.Namespace], None]


@dataclass(frozen=True)
class StandardModelSpec:
    """Declarative public contract for a standard video-generation model."""

    canonical_id: str
    resolution_choices: tuple[str, ...]
    default_resolution: str
    ratio_choices: tuple[str, ...]
    default_ratio: str
    duration_choices: tuple[int, ...]
    default_duration: int
    supports_audio: bool
    default_audio: bool | None
    supports_first_frame: bool
    supports_last_frame: bool
    max_reference_images: int
    validate: StandardValidation | None = None
    reference_image_role: str | None = None


def require_first_frame_for_last_frame(args: argparse.Namespace) -> None:
    """Reject a last-frame-only request where the model requires a first frame."""

    if getattr(args, "last_frame", None) and not getattr(args, "first_frame", None):
        raise UserError("--last-frame requires --first-frame for this model.")


class _StandardArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args: Any, spec: StandardModelSpec, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._standard_spec = spec

    def parse_args(
        self, args: list[str] | None = None, namespace: argparse.Namespace | None = None
    ) -> argparse.Namespace:
        parsed = super().parse_args(args, namespace)
        if self._standard_spec.validate is not None:
            try:
                self._standard_spec.validate(parsed)
            except UserError as exc:
                self.error(str(exc))
        return parsed


def build_standard_parser(spec: StandardModelSpec) -> argparse.ArgumentParser:
    """Build the shared create/run CLI while exposing only a model's capabilities."""

    parser = _StandardArgumentParser(description=spec.canonical_id, spec=spec)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--trust-custom-base-url", action="store_true")
    parser.add_argument("--allow-insecure-localhost", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--timeout", type=positive_float, default=60)
    commands = parser.add_subparsers(
        dest="command", required=True, parser_class=argparse.ArgumentParser
    )

    for command_name, help_text in (
        ("create", "create one paid video task"),
        ("run", "create, wait for, and optionally download one paid video task"),
    ):
        command = commands.add_parser(command_name, help=help_text)
        command.add_argument("--prompt")
        command.add_argument("--prompt-file")
        command.add_argument(
            "--resolution", choices=spec.resolution_choices, default=spec.default_resolution
        )
        command.add_argument("--ratio", choices=spec.ratio_choices, default=spec.default_ratio)
        command.add_argument(
            "--duration", type=positive_int, choices=spec.duration_choices,
            default=spec.default_duration,
        )
        if spec.supports_audio:
            command.add_argument(
                "--generate-audio",
                action=argparse.BooleanOptionalAction,
                default=spec.default_audio,
            )
        if spec.supports_first_frame:
            command.add_argument("--first-frame", type=validate_https_url)
        if spec.supports_last_frame:
            command.add_argument("--last-frame", type=validate_https_url)
        if spec.max_reference_images:
            command.add_argument(
                "--reference-image",
                action="append",
                default=[],
                type=validate_https_url,
            )
        command.add_argument("--confirm-paid", action="store_true")
        command.add_argument("--dry-run", action="store_true")
        command.add_argument("--idempotency-key")
        if command_name == "run":
            command.add_argument("--output")
            command.add_argument("--overwrite", action="store_true")
            command.add_argument("--interval", type=positive_float, default=5)
            command.add_argument("--max-wait", type=positive_float, default=900)
    return parser


def build_standard_payload(spec: StandardModelSpec, args: argparse.Namespace) -> dict[str, Any]:
    """Validate one standard-model request and return its public API payload."""

    if spec.validate is not None:
        spec.validate(args)
    prompt = load_prompt(args.prompt, args.prompt_file)
    content: list[dict[str, str]] = []
    first_frame = getattr(args, "first_frame", None)
    last_frame = getattr(args, "last_frame", None)
    if first_frame:
        content.append(
            {"type": "image_url", "image_url": first_frame, "role": "first_frame"}
        )
    if last_frame:
        content.append(
            {"type": "image_url", "image_url": last_frame, "role": "last_frame"}
        )
    for image_url in getattr(args, "reference_image", []):
        image = {"type": "image_url", "image_url": image_url}
        if spec.reference_image_role is not None:
            image["role"] = spec.reference_image_role
        content.append(image)

    if len(getattr(args, "reference_image", [])) > spec.max_reference_images:
        raise UserError(
            f"This model supports at most {spec.max_reference_images} reference images."
        )

    payload: dict[str, Any] = {
        "model": spec.canonical_id,
        "prompt": prompt,
        "resolution": args.resolution,
        "ratio": "adaptive" if first_frame or last_frame else args.ratio,
        "duration": args.duration,
    }
    if content:
        payload["content"] = content
    if spec.supports_audio:
        payload["generate_audio"] = args.generate_audio
    return payload


def run_standard_model(spec: StandardModelSpec, argv: list[str] | None = None) -> int:
    """Run the declarative create/run flow without retrying the paid POST."""

    args = build_standard_parser(spec).parse_args(argv)
    try:
        payload = build_standard_payload(spec, args)
        if args.dry_run:
            emit_result(payload, json_mode=args.json)
            return 0
        if not args.confirm_paid:
            raise UserError("--confirm-paid is required before creating a paid video task.")

        base_url = normalize_base_url(
            args.base_url,
            trust_custom=args.trust_custom_base_url,
            allow_insecure_localhost=args.allow_insecure_localhost,
        )
        api_key, _source = resolve_api_key()
        idempotency_key = (
            validate_idempotency_key(args.idempotency_key)
            if args.idempotency_key
            else new_idempotency_key()
        )
        _status, response = request_json(
            "POST",
            f"{base_url}/v1/videos/generations",
            api_key,
            payload=payload,
            headers={"Idempotency-Key": idempotency_key},
            timeout=args.timeout,
        )
        task = _task_object(response)
        task_id = task.get("id")
        if not isinstance(task_id, str) or not task_id:
            raise ProtocolError("Create response did not include a task id.", response=task)
        result = dict(task)
        result["idempotency_key"] = idempotency_key
        result.setdefault("summary", f"Task created: {task_id}")

        if args.command == "run":
            task = poll_task(
                base_url,
                task_id,
                api_key,
                wait=True,
                interval=args.interval,
                max_wait=args.max_wait,
                timeout=args.timeout,
            )
            result = dict(task)
            result["idempotency_key"] = idempotency_key
            status = task.get("status")
            if status != "succeeded":
                result.setdefault("summary", f"Task {task_id} ended with status {status}.")
                emit_result(result, json_mode=args.json)
                return 1
            if args.output:
                output = download_task(
                    base_url,
                    task_id,
                    args.output,
                    api_key,
                    overwrite=args.overwrite,
                    timeout=args.timeout,
                )
                result["output"] = str(output)
            result.setdefault("summary", f"Task succeeded: {task_id}")

        emit_result(result, json_mode=args.json)
        return 0
    except (UserError, ProtocolError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Surface API redirects as errors instead of issuing another request."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


_NO_REDIRECT_OPENER = urllib.request.build_opener(_NoRedirectHandler())


def resolve_api_key(*, required: bool = True) -> tuple[str, str]:
    """Return the first configured API key and the environment variable used."""

    for env_name in KEY_ENV_ORDER:
        value = os.environ.get(env_name)
        if value:
            return value, env_name
    if not required:
        return "", ""
    raise UserError(
        "Missing API key. Set OPENAI_API_KEY or ANTHROPIC_AUTH_TOKEN."
    )


def load_prompt(prompt: str | None, prompt_file: str | os.PathLike[str] | None) -> str:
    """Load one non-empty prompt from either a CLI value or a UTF-8 file."""

    if prompt is not None and prompt_file is not None:
        raise UserError("Use either --prompt or --prompt-file, not both.")
    if prompt_file is not None:
        try:
            value = Path(prompt_file).expanduser().read_text(encoding="utf-8")
        except OSError as exc:
            raise UserError(f"Could not read prompt file: {exc}") from None
    else:
        value = prompt or ""
    value = value.strip()
    if not value:
        raise UserError("A non-empty --prompt or --prompt-file is required.")
    return value


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be an integer") from None
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than 0")
    return parsed


def positive_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a number") from None
    if not math.isfinite(parsed) or parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than 0")
    return parsed


def validate_https_url(value: str) -> str:
    """Accept a public-reference-shaped HTTPS URL, never data or local paths."""

    try:
        parsed = urllib.parse.urlsplit(value)
        _ = parsed.port
    except ValueError:
        raise argparse.ArgumentTypeError("must be a valid HTTPS URL") from None
    if (
        parsed.scheme.lower() != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise argparse.ArgumentTypeError("must be a public HTTPS URL")
    hostname = parsed.hostname.lower()
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        if not address.is_global:
            raise argparse.ArgumentTypeError("must use a globally routable HTTPS host")
        return value
    if (
        hostname in LOCAL_REFERENCE_HOSTS
        or hostname.endswith(LOCAL_REFERENCE_HOST_SUFFIXES)
        or "." not in hostname
    ):
        raise argparse.ArgumentTypeError("must use a public HTTPS host")
    if re.fullmatch(r"[0-9.]+", hostname):
        raise argparse.ArgumentTypeError("must use a public HTTPS host")
    return value


def validate_idempotency_key(value: str) -> str:
    """Validate a caller key without normalizing or otherwise changing it."""

    if not value:
        raise UserError("Idempotency key must not be empty.")
    if len(value) > MAX_IDEMPOTENCY_KEY_LENGTH:
        raise UserError("Idempotency key must be at most 128 characters.")
    if "\r" in value or "\n" in value:
        raise UserError("Idempotency key must not contain line breaks.")
    return value


def new_idempotency_key() -> str:
    """Return a caller-visible key suitable for one paid create operation."""

    return "idem_" + secrets.token_hex(16)


def _is_loopback(hostname: str) -> bool:
    if hostname.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def normalize_base_url(
    base_url: str,
    *,
    trust_custom: bool = False,
    allow_insecure_localhost: bool = False,
) -> str:
    """Validate the API trust boundary and return a slash-free base URL."""

    if not base_url or base_url != base_url.strip():
        raise UserError("Base URL must be a non-empty URL without surrounding spaces.")
    try:
        parsed = urllib.parse.urlsplit(base_url)
        port = parsed.port
    except ValueError as exc:
        raise UserError(f"Invalid base URL: {exc}") from None
    hostname = parsed.hostname
    if not hostname or parsed.username is not None or parsed.password is not None:
        raise UserError("Base URL must not contain userinfo and must include a host.")
    if parsed.query or parsed.fragment:
        raise UserError("Base URL must not contain a query string or fragment.")
    if parsed.path not in {"", "/"}:
        raise UserError("Base URL must not contain a path.")

    scheme = parsed.scheme.lower()
    hostname = hostname.lower()
    if scheme == "https":
        if hostname not in OFFICIAL_HOSTS and not trust_custom:
            raise UserError(
                "Custom API hosts require --trust-custom-base-url."
            )
    elif scheme == "http":
        if not (
            trust_custom
            and allow_insecure_localhost
            and _is_loopback(hostname)
        ):
            raise UserError(
                "HTTP is allowed only for loopback with --trust-custom-base-url "
                "and --allow-insecure-localhost."
            )
    else:
        raise UserError("Base URL must use HTTPS.")

    host_text = f"[{hostname}]" if ":" in hostname else hostname
    if port is not None:
        host_text += f":{port}"
    return f"{scheme}://{host_text}"


_URL_WITH_QUERY = re.compile(r"https?://[^\s\"'<>]+\?[^\s\"'<>]+")


def _sanitize_text(text: str, api_key: str | None) -> str:
    if api_key:
        text = text.replace(api_key, "<redacted>")

    def redact_query(match: re.Match[str]) -> str:
        url = match.group(0)
        prefix, _separator, _query = url.partition("?")
        return prefix + "?<redacted>"

    return _URL_WITH_QUERY.sub(redact_query, text)


def _sanitize_response(value: Any, api_key: str | None) -> Any:
    if isinstance(value, str):
        return _sanitize_text(value, api_key)
    if isinstance(value, list):
        return [_sanitize_response(item, api_key) for item in value]
    if isinstance(value, dict):
        return {
            (
                _sanitize_text(key, api_key) if isinstance(key, str) else key
            ): _sanitize_response(item, api_key)
            for key, item in value.items()
        }
    return value


def _error_code(response: Any) -> str | None:
    if not isinstance(response, dict):
        return None
    error = response.get("error")
    if isinstance(error, dict):
        for name in ("code", "type"):
            if isinstance(error.get(name), str):
                return error[name]
    for name in ("code", "type"):
        if isinstance(response.get(name), str):
            return response[name]
    return None


def request_json(
    method: str,
    url: str,
    api_key: str | None = None,
    *,
    payload: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
    timeout: float = 60,
) -> tuple[int, Any]:
    """Perform exactly one HTTP request and decode its JSON response."""

    method = method.upper()
    request_headers = dict(headers or {})
    if api_key:
        request_headers.setdefault("Authorization", f"Bearer {api_key}")
    for name, value in request_headers.items():
        if name.lower() == "idempotency-key":
            validate_idempotency_key(value)

    data = None
    if payload is not None:
        try:
            data = json.dumps(
                payload, ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise UserError(f"Request payload is not JSON serializable: {exc}") from None
        request_headers.setdefault("Content-Type", "application/json")
    request_headers.setdefault("Accept", "application/json")
    request = urllib.request.Request(
        url, data=data, headers=request_headers, method=method
    )

    try:
        with _NO_REDIRECT_OPENER.open(request, timeout=timeout) as response:
            status = response.status
            body = response.read()
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read()
        finally:
            exc.close()
        text = body.decode("utf-8", errors="replace")
        try:
            parsed: Any = json.loads(text)
        except json.JSONDecodeError:
            parsed = {"error": {"message": text or exc.reason}}
        parsed = _sanitize_response(parsed, api_key)
        code = _error_code(parsed)
        detail = json.dumps(parsed, ensure_ascii=False, separators=(",", ":"))
        detail = _sanitize_text(detail, api_key)
        uncertain = method == "POST" and (
            exc.code >= 500 or code == "submission_unknown"
        )
        raise ProtocolError(
            f"HTTP {exc.code}: {detail}",
            status=exc.code,
            error_code=code,
            response=parsed,
            uncertain=uncertain,
        ) from None
    except (
        urllib.error.URLError,
        TimeoutError,
        socket.timeout,
        http.client.RemoteDisconnected,
        ConnectionError,
        OSError,
    ) as exc:
        reason = getattr(exc, "reason", exc)
        message = _sanitize_text(str(reason), api_key)
        raise ProtocolError(
            f"Network error: {message}", uncertain=method == "POST"
        ) from None

    if not body:
        return status, {}
    try:
        return status, json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        message = _sanitize_text(str(exc), api_key)
        raise ProtocolError(
            f"Response was not valid JSON: {message}", status=status
        ) from None


def task_url(base_url: str, task_id: str, suffix: str = "") -> str:
    """Build one task URL while keeping the opaque ID in one path segment."""

    if not task_id:
        raise UserError("Task ID must not be empty.")
    if suffix and not suffix.startswith("/"):
        suffix = "/" + suffix
    encoded_id = urllib.parse.quote(task_id, safe="")
    return f"{base_url.rstrip('/')}/v1/videos/generations/{encoded_id}{suffix}"


def _task_object(response: Any) -> dict[str, Any]:
    if not isinstance(response, dict):
        raise ProtocolError("Task response must be a JSON object.", response=response)
    return response


def poll_task(
    base_url: str,
    task_id: str,
    api_key: str | None = None,
    *,
    wait: bool = False,
    interval: float = 5,
    max_wait: float = 900,
    timeout: float = 60,
) -> dict[str, Any]:
    """Fetch a task once or wait while it remains queued/running."""

    started = time.monotonic()
    while True:
        _status, response = request_json(
            "GET", task_url(base_url, task_id), api_key, timeout=timeout
        )
        task = _task_object(response)
        status = task.get("status")
        if not wait or status in TASK_STATUSES_TERMINAL:
            return task
        if status not in TASK_STATUSES_IN_PROGRESS:
            return task

        elapsed = time.monotonic() - started
        if elapsed + interval > max_wait:
            raise ProtocolError(
                "Maximum wait reached before the task completed.", response=task
            )
        time.sleep(interval)


def delete_task(
    base_url: str,
    task_id: str,
    api_key: str | None = None,
    *,
    timeout: float = 60,
) -> Any:
    """Delete one existing task with exactly one HTTP request."""

    _status, response = request_json(
        "DELETE", task_url(base_url, task_id), api_key, timeout=timeout
    )
    return response


def _origin(url: str) -> tuple[str, str, int | None]:
    parsed = urllib.parse.urlsplit(url)
    return parsed.scheme.lower(), (parsed.hostname or "").lower(), parsed.port


def _validate_download_redirect(current_url: str, location: str) -> str:
    """Resolve one download redirect without weakening the transport boundary."""

    redirected = urllib.parse.urljoin(current_url, location)
    try:
        current = urllib.parse.urlsplit(current_url)
        parsed = urllib.parse.urlsplit(redirected)
        _ = parsed.port
    except ValueError as exc:
        raise ProtocolError(f"Invalid download redirect: {exc}") from None
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ProtocolError("Invalid download redirect URL.")
    current_scheme = current.scheme.lower()
    redirected_scheme = parsed.scheme.lower()
    if current_scheme == "https" and redirected_scheme == "http":
        raise ProtocolError("Refusing HTTPS to HTTP download redirect.")
    if redirected_scheme == "http" and (
        current_scheme != "http"
        or not current.hostname
        or not _is_loopback(current.hostname)
        or not _is_loopback(parsed.hostname)
    ):
        raise ProtocolError(
            "HTTP download redirects must remain within explicitly authorized "
            "loopback hosts."
        )
    return redirected


def _download_error(exc: urllib.error.HTTPError, api_key: str | None) -> ProtocolError:
    try:
        body = exc.read()
    finally:
        exc.close()
    text = body.decode("utf-8", errors="replace")
    try:
        parsed: Any = json.loads(text)
    except json.JSONDecodeError:
        parsed = {"error": {"message": text or exc.reason}}
    parsed = _sanitize_response(parsed, api_key)
    code = _error_code(parsed)
    detail = _sanitize_text(
        json.dumps(parsed, ensure_ascii=False, separators=(",", ":")), api_key
    )
    return ProtocolError(
        f"HTTP {exc.code}: {detail}",
        status=exc.code,
        error_code=code,
        response=parsed,
    )


def download_task(
    base_url: str,
    task_id: str,
    output: str | os.PathLike[str],
    api_key: str | None = None,
    *,
    overwrite: bool = False,
    timeout: float = 60,
) -> Path:
    """Download task content privately, then atomically publish the completed file."""

    destination = Path(output).expanduser()
    part = Path(str(destination) + ".part")
    if destination.exists() and not overwrite:
        raise UserError(f"Output exists; use --overwrite to replace it: {destination}")
    if part.exists():
        raise UserError(f"Refusing to overwrite existing partial file: {part}")
    if not destination.parent.is_dir():
        raise UserError(f"Output directory does not exist: {destination.parent}")

    url = task_url(base_url, task_id, "/content")
    authorization = f"Bearer {api_key}" if api_key else None
    redirects = 0
    response: Any = None

    while True:
        headers = {"Accept": "video/mp4"}
        if authorization:
            headers["Authorization"] = authorization
        request = urllib.request.Request(url, headers=headers, method="GET")
        try:
            response = _NO_REDIRECT_OPENER.open(request, timeout=timeout)
            break
        except urllib.error.HTTPError as exc:
            if exc.code not in {301, 302, 303, 307, 308}:
                raise _download_error(exc, api_key) from None
            location = exc.headers.get("Location")
            exc.close()
            if not location:
                raise ProtocolError(
                    "Download redirect did not include a Location header."
                )
            if redirects >= MAX_DOWNLOAD_REDIRECTS:
                raise ProtocolError("Download redirect limit exceeded.")
            redirected = _validate_download_redirect(url, location)
            if _origin(redirected) != _origin(url):
                authorization = None
            url = redirected
            redirects += 1
        except (
            urllib.error.URLError,
            TimeoutError,
            socket.timeout,
            http.client.RemoteDisconnected,
            ConnectionError,
            OSError,
        ) as exc:
            reason = getattr(exc, "reason", exc)
            raise ProtocolError(
                f"Network error: {_sanitize_text(str(reason), api_key)}"
            ) from None

    created_part = False
    try:
        if response.status not in {200, 206}:
            raise ProtocolError(
                f"Unexpected download HTTP status: {response.status}",
                status=response.status,
            )
        expected_length_text = response.headers.get("Content-Length")
        try:
            expected_length = (
                int(expected_length_text)
                if expected_length_text is not None
                else None
            )
        except ValueError:
            raise ProtocolError("Download Content-Length was not an integer.") from None
        fd = os.open(part, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        created_part = True
        received = 0
        with os.fdopen(fd, "wb") as file_handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                file_handle.write(chunk)
                received += len(chunk)
            file_handle.flush()
            os.fsync(file_handle.fileno())
        if expected_length is not None and received != expected_length:
            raise ProtocolError(
                f"Truncated download: expected {expected_length} bytes, received {received}."
            )
        os.chmod(part, 0o600)
        if destination.exists() and not overwrite:
            raise UserError(
                f"Output appeared during download; use --overwrite: {destination}"
            )
        os.replace(part, destination)
        created_part = False
        return destination
    except (ProtocolError, UserError):
        raise
    except (OSError, http.client.IncompleteRead) as exc:
        raise ProtocolError(
            f"Download failed: {_sanitize_text(str(exc), api_key)}"
        ) from None
    finally:
        response.close()
        if created_part:
            try:
                part.unlink()
            except FileNotFoundError:
                pass


def emit_result(result: Mapping[str, Any], *, json_mode: bool) -> None:
    """Emit one JSON document to stdout or human-readable status to stderr."""

    if json_mode:
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        return
    summary = result.get("summary")
    if not isinstance(summary, str) or not summary:
        summary = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
    print(summary, file=sys.stderr)
