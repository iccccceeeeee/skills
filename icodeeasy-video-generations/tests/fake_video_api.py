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

            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length)
                owner.requests.append(
                    {
                        "method": "POST",
                        "path": self.path,
                        "headers": dict(self.headers.items()),
                        "body": body,
                    }
                )

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
                    self._json(401, {"error": {"message": f"bad {secret} at {signed}"}})
                    return
                if self.path.startswith("/v1/videos/generations"):
                    self._generation(body)
                    return

                self._json(202, {"ok": True})

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
                if "disconnect=1" in self.path:
                    self.connection.shutdown(2)
                    self.connection.close()
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
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

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
