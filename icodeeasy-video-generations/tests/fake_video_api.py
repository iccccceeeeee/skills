"""Loopback-only fake API used by the video common-module tests."""

from __future__ import annotations

import hashlib
import json
import threading
import time
from contextlib import AbstractContextManager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


class _Server(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request: object, client_address: object) -> None:
        # Tests deliberately disconnect clients and time out responses.
        return


class FakeVideoAPI(AbstractContextManager["FakeVideoAPI"]):
    """Small stateful HTTP service with request recording and idempotency."""

    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        self.tasks: dict[str, tuple[bytes, str]] = {}
        self.created_task_count = 0
        self.redirect_target: str | None = None
        self.disconnect_after_create = False
        self.truncate_create_response = False
        self.invalid_create_response = False
        self.invalid_http_status_after_create = False
        self.create_error_status: int | None = None
        self.truncate_error_response = False
        self.poll_error_status: int | None = None
        self.download_error_status: int | None = None
        self._server: _Server | None = None
        self._thread: threading.Thread | None = None

    @property
    def base_url(self) -> str:
        if self._server is None:
            raise RuntimeError("fake API is not running")
        host, port = self._server.server_address
        return f"http://{host}:{port}"

    def __enter__(self) -> "FakeVideoAPI":
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, format: str, *args: object) -> None:
                return

            def do_GET(self) -> None:
                self._record(b"")
                if self.path.startswith("/v1/videos/tasks/"):
                    if self.path.endswith("/content") and owner.download_error_status is not None:
                        self._json(
                            owner.download_error_status,
                            {"error": {"code": "download_failed"}},
                        )
                        return
                    if self.path.endswith("/content"):
                        self._raw(200, b"\x00\x00\x00\x18ftypmp42" + b"video-data" * 10, "video/mp4")
                        return
                    if owner.poll_error_status is not None:
                        self._json(
                            owner.poll_error_status,
                            {"error": {"code": "poll_failed"}},
                        )
                        return
                    self._json(200, {"id": self.path.rsplit("/", 1)[-1], "status": "succeeded"})
                    return
                self._json(200, {"ok": True})

            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length)
                self._record(body)

                if self.path == "/redirect":
                    if owner.redirect_target is None:
                        self._json(500, {"error": {"code": "missing_redirect_target"}})
                        return
                    self.send_response(302)
                    self.send_header("Location", owner.redirect_target)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return

                if self.path == "/disconnect":
                    self.connection.shutdown(2)
                    self.connection.close()
                    return
                if self.path == "/timeout":
                    time.sleep(0.2)
                    self._json(202, {"id": "vid_too_late"})
                    return
                if self.path in {"/502", "/503"}:
                    status = int(self.path[1:])
                    self._json(status, {"error": {"code": f"upstream_{status}"}})
                    return
                if self.path == "/non-json-error":
                    self._raw(500, b"upstream exploded", "text/plain")
                    return
                if self.path == "/secret-error":
                    secret = self.headers.get("Authorization", "").removeprefix("Bearer ")
                    signed = "https://media.example/video.mp4?token=signed-secret&expires=1"
                    self._json(
                        401,
                        {
                            "error": {
                                "message": f"bad {secret} at {signed}",
                                f"credential-{secret}": f"echo-{secret}",
                                signed: signed,
                            }
                        },
                    )
                    return
                if self.path.startswith("/v1/videos/generations"):
                    self._generation(body)
                    return

                self._json(202, {"ok": True})

            def _record(self, body: bytes) -> None:
                owner.requests.append(
                    {
                        "method": self.command,
                        "path": self.path,
                        "headers": dict(self.headers.items()),
                        "body": body,
                    }
                )

            def _generation(self, body: bytes) -> None:
                key = self.headers.get("Idempotency-Key", "")
                normalized = json.dumps(
                    json.loads(body), sort_keys=True, separators=(",", ":")
                ).encode("utf-8")
                existing = owner.tasks.get(key)
                if existing is not None:
                    previous_body, task_id = existing
                    if previous_body != normalized:
                        self._json(
                            409,
                            {
                                "error": {
                                    "code": "idempotency_conflict",
                                    "message": "key already used with another payload",
                                }
                            },
                        )
                        return
                    self._json(202, {"id": task_id, "status": "queued"})
                    return

                owner.created_task_count += 1
                digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
                task_id = f"vid_{digest}"
                owner.tasks[key] = (normalized, task_id)
                if owner.disconnect_after_create or "disconnect=1" in self.path:
                    self.connection.shutdown(2)
                    self.connection.close()
                    return
                if owner.invalid_http_status_after_create:
                    self.wfile.write(b"invalid HTTP status line\r\n\r\n")
                    self.close_connection = True
                    return
                if owner.invalid_create_response:
                    self._json(202, [{"id": task_id, "status": "queued"}])
                    return
                if owner.create_error_status is not None:
                    self._json(owner.create_error_status, {"error": {"code": "submission_unknown"}})
                    return
                if owner.truncate_create_response:
                    body = json.dumps({"id": task_id, "status": "queued"}).encode()
                    self.send_response(202)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body) + 100))
                    self.end_headers()
                    self.wfile.write(body)
                    self.close_connection = True
                    return
                self._json(202, {"id": task_id, "status": "queued"})

            def _json(self, status: int, payload: dict[str, Any]) -> None:
                self._raw(
                    status,
                    json.dumps(payload, separators=(",", ":")).encode("utf-8"),
                    "application/json",
                )

            def _raw(self, status: int, body: bytes, content_type: str) -> None:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                truncated = owner.truncate_error_response and status >= 400
                self.send_header("Content-Length", str(len(body) + (100 if truncated else 0)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass
                if truncated:
                    self.close_connection = True

        self._server = _Server(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2)
