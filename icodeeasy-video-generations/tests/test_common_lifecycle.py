"""Existing video-task lifecycle contracts."""

from __future__ import annotations

import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _video_common import ProtocolError, delete_task, poll_task, task_url  # noqa: E402


class _LifecycleServer:
    def __init__(self, responses: list[tuple[int, dict[str, object]]]) -> None:
        self.responses = responses
        self.requests: list[dict[str, object]] = []
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def base_url(self) -> str:
        assert self._server is not None
        host, port = self._server.server_address
        return f"http://{host}:{port}"

    def __enter__(self) -> "_LifecycleServer":
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, format: str, *args: object) -> None:
                return

            def do_GET(self) -> None:
                self._respond()

            def do_DELETE(self) -> None:
                self._respond()

            def _respond(self) -> None:
                owner.requests.append(
                    {
                        "method": self.command,
                        "path": self.path,
                        "authorization": self.headers.get("Authorization"),
                    }
                )
                index = min(len(owner.requests) - 1, len(owner.responses) - 1)
                status, payload = owner.responses[index]
                body = json.dumps(payload).encode("utf-8") if payload else b""
                self.send_response(status)
                if body:
                    self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                if body:
                    self.wfile.write(body)

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        assert self._server is not None and self._thread is not None
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)


class LifecycleTests(unittest.TestCase):
    def test_task_id_is_encoded_as_exactly_one_path_segment(self) -> None:
        self.assertEqual(
            task_url("https://api.icodeeasy.cc", "folder/id ?#", "/content"),
            "https://api.icodeeasy.cc/v1/videos/generations/folder%2Fid%20%3F%23/content",
        )

    def test_one_shot_poll_returns_first_task_without_waiting(self) -> None:
        with _LifecycleServer([(200, {"id": "vid_1", "status": "queued"})]) as api:
            task = poll_task(api.base_url, "vid_1", "secret", timeout=1)

        self.assertEqual(task["status"], "queued")
        self.assertEqual(len(api.requests), 1)

    def test_wait_polls_until_succeeded(self) -> None:
        responses = [
            (200, {"id": "vid_1", "status": "queued"}),
            (200, {"id": "vid_1", "status": "running"}),
            (200, {"id": "vid_1", "status": "succeeded"}),
        ]
        with _LifecycleServer(responses) as api:
            task = poll_task(
                api.base_url,
                "vid_1",
                "secret",
                wait=True,
                interval=0.001,
                max_wait=1,
                timeout=1,
            )

        self.assertEqual(task["status"], "succeeded")
        self.assertEqual(len(api.requests), 3)

    def test_failed_and_unknown_statuses_are_returned_without_more_polls(self) -> None:
        for status in ("failed", "paused-by-provider"):
            with self.subTest(status=status), _LifecycleServer(
                [(200, {"id": "vid_1", "status": status})]
            ) as api:
                task = poll_task(
                    api.base_url,
                    "vid_1",
                    wait=True,
                    interval=0.001,
                    max_wait=1,
                    timeout=1,
                )
                self.assertEqual(task["status"], status)
                self.assertEqual(len(api.requests), 1)

    def test_max_wait_raises_with_the_last_task_attached(self) -> None:
        queued = {"id": "vid_1", "status": "queued"}
        with _LifecycleServer([(200, queued)]) as api:
            with self.assertRaisesRegex(ProtocolError, "Maximum wait") as caught:
                poll_task(
                    api.base_url,
                    "vid_1",
                    wait=True,
                    interval=0.01,
                    max_wait=0.001,
                    timeout=1,
                )

        self.assertEqual(caught.exception.response, queued)
        self.assertEqual(len(api.requests), 1)

    def test_delete_accepts_204_and_does_not_retry_unsafe_409(self) -> None:
        with _LifecycleServer([(204, {})]) as api:
            result = delete_task(api.base_url, "vid_1", "secret", timeout=1)
        self.assertEqual(result, {})
        self.assertEqual(len(api.requests), 1)

        error = {"error": {"code": "video_delete_unsafe"}}
        with _LifecycleServer([(409, error)]) as api:
            with self.assertRaises(ProtocolError) as caught:
                delete_task(api.base_url, "vid_1", "secret", timeout=1)
        self.assertEqual(caught.exception.error_code, "video_delete_unsafe")
        self.assertEqual(len(api.requests), 1)


if __name__ == "__main__":
    unittest.main()
