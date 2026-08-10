"""Safe existing-task download contracts."""

from __future__ import annotations

import stat
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _video_common import (  # noqa: E402
    ProtocolError,
    UserError,
    _validate_download_redirect,
    download_task,
)
import _video_common  # noqa: E402


MP4 = b"\x00\x00\x00\x18ftypmp42test-video-bytes"


class _DownloadServer:
    def __init__(self) -> None:
        self.requests: list[dict[str, str | None]] = []
        self.redirect_target: str | None = None
        self.redirect_forever = False
        self.status = 200
        self.body = MP4
        self.claimed_length: int | None = None
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def base_url(self) -> str:
        assert self._server is not None
        host, port = self._server.server_address
        return f"http://{host}:{port}"

    def __enter__(self) -> "_DownloadServer":
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, format: str, *args: object) -> None:
                return

            def do_GET(self) -> None:
                owner.requests.append(
                    {
                        "path": self.path,
                        "authorization": self.headers.get("Authorization"),
                    }
                )
                if owner.redirect_target is not None:
                    target = owner.redirect_target
                    if owner.redirect_forever:
                        target = owner.base_url + "/redirect-again"
                    self.send_response(302)
                    self.send_header("Location", target)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return

                self.send_response(owner.status)
                self.send_header("Content-Type", "video/mp4")
                length = owner.claimed_length
                self.send_header("Content-Length", str(length or len(owner.body)))
                self.end_headers()
                self.wfile.write(owner.body)
                if length is not None and length > len(owner.body):
                    self.close_connection = True

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        assert self._server is not None and self._thread is not None
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)


class DownloadTests(unittest.TestCase):
    def test_authenticated_200_and_206_create_private_mp4_atomically(self) -> None:
        for status_code in (200, 206):
            with self.subTest(status=status_code), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp) / "video.mp4"
                with _DownloadServer() as api:
                    api.status = status_code
                    result = download_task(
                        api.base_url, "vid_1", output, "download-secret", timeout=1
                    )

                self.assertEqual(output.read_bytes(), MP4)
                self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
                self.assertFalse(Path(str(output) + ".part").exists())
                self.assertEqual(
                    api.requests[0]["authorization"], "Bearer download-secret"
                )
                self.assertEqual(result, output)

    def test_cross_origin_redirect_does_not_forward_authorization(self) -> None:
        with (
            tempfile.TemporaryDirectory() as tmp,
            _DownloadServer() as target,
            _DownloadServer() as source,
        ):
            source.redirect_target = target.base_url + "/media.mp4"
            output = Path(tmp) / "video.mp4"

            download_task(source.base_url, "vid_1", output, "redirect-secret", timeout=1)
            self.assertEqual(
                source.requests[0]["authorization"], "Bearer redirect-secret"
            )
            self.assertIsNone(target.requests[0]["authorization"])
            self.assertEqual(output.read_bytes(), MP4)

    def test_more_than_one_redirect_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, _DownloadServer() as api:
            api.redirect_target = api.base_url + "/redirect-again"
            api.redirect_forever = True
            output = Path(tmp) / "video.mp4"

            with self.assertRaisesRegex(ProtocolError, "redirect"):
                download_task(api.base_url, "vid_1", output, "secret", timeout=1)
            self.assertEqual(len(api.requests), 2)
            self.assertFalse(output.exists())

    def test_https_to_http_redirect_is_rejected_before_target_request(self) -> None:
        with _DownloadServer() as target:
            with self.assertRaisesRegex(ProtocolError, "HTTPS.*HTTP"):
                _validate_download_redirect(
                    "https://api.icodeeasy.cc/v1/videos/generations/vid_1/content",
                    target.base_url + "/media.mp4",
                )

        self.assertEqual(target.requests, [])

    def test_loopback_http_download_cannot_redirect_to_non_loopback_http(self) -> None:
        with self.assertRaisesRegex(ProtocolError, "loopback"):
            _validate_download_redirect(
                "http://127.0.0.1:8123/v1/videos/generations/vid_1/content",
                "http://192.0.2.10/media.mp4",
            )

    def test_truncated_response_preserves_existing_destination(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, _DownloadServer() as api:
            output = Path(tmp) / "video.mp4"
            output.write_bytes(b"existing-good-video")
            api.claimed_length = len(MP4) + 100

            with self.assertRaises(ProtocolError):
                download_task(
                    api.base_url,
                    "vid_1",
                    output,
                    "secret",
                    overwrite=True,
                    timeout=1,
                )
            self.assertEqual(output.read_bytes(), b"existing-good-video")
            self.assertFalse(Path(str(output) + ".part").exists())

    def test_existing_destination_is_refused_without_overwrite_before_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, _DownloadServer() as api:
            output = Path(tmp) / "video.mp4"
            output.write_bytes(b"existing")

            with self.assertRaisesRegex(UserError, "overwrite"):
                download_task(api.base_url, "vid_1", output, "secret", timeout=1)
            self.assertEqual(api.requests, [])
            self.assertEqual(output.read_bytes(), b"existing")

    def test_existing_part_file_is_not_reused_or_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, _DownloadServer() as api:
            output = Path(tmp) / "video.mp4"
            part = Path(str(output) + ".part")
            part.write_bytes(b"untrusted-partial")

            with self.assertRaisesRegex(UserError, "part"):
                download_task(api.base_url, "vid_1", output, "secret", timeout=1)
            self.assertEqual(part.read_bytes(), b"untrusted-partial")
            self.assertEqual(api.requests, [])

    def test_destination_appearing_during_download_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, _DownloadServer() as api:
            output = Path(tmp) / "video.mp4"
            original_link = _video_common.os.link

            def create_destination_before_publish(
                source: str | Path, destination: str | Path, *args: object, **kwargs: object
            ) -> None:
                output.write_bytes(b"appeared-during-download")
                original_link(source, destination, *args, **kwargs)

            with patch.object(
                _video_common.os, "link", side_effect=create_destination_before_publish
            ):
                with self.assertRaisesRegex(UserError, "appeared during download"):
                    download_task(api.base_url, "vid_1", output, "secret", timeout=1)

            self.assertEqual(output.read_bytes(), b"appeared-during-download")
            self.assertFalse(Path(str(output) + ".part").exists())


if __name__ == "__main__":
    unittest.main()
