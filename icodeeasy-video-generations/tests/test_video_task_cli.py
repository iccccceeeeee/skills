"""Command-line contracts for existing video tasks."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS))

from test_common_lifecycle import _LifecycleServer


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "video_task.py"


def _run(*args: str, api_key: str | None = "cli-secret") -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.pop("OPENAI_API_KEY", None)
    environment.pop("ANTHROPIC_AUTH_TOKEN", None)
    if api_key is not None:
        environment["OPENAI_API_KEY"] = api_key
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        capture_output=True,
        env=environment,
        timeout=5,
    )


def _base_args(base_url: str) -> tuple[str, ...]:
    return (
        "--base-url",
        base_url,
        "--trust-custom-base-url",
        "--allow-insecure-localhost",
        "--json",
    )


class VideoTaskCLITests(unittest.TestCase):
    def test_poll_success_prints_one_json_document_and_exits_zero(self) -> None:
        with _LifecycleServer([(200, {"id": "vid_1", "status": "succeeded"})]) as api:
            result = _run(*_base_args(api.base_url), "poll", "vid_1")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "succeeded")
        self.assertEqual(result.stdout.count("\n"), 1)

    def test_poll_terminal_failure_unknown_status_and_max_wait_exit_one(self) -> None:
        cases = (
            ({"id": "vid_1", "status": "failed"}, ()),
            ({"id": "vid_1", "status": "mystery"}, ()),
            (
                {"id": "vid_1", "status": "queued"},
                ("--wait", "--interval", "0.01", "--max-wait", "0.001"),
            ),
        )
        for payload, options in cases:
            with self.subTest(status=payload["status"]), _LifecycleServer([(200, payload)]) as api:
                result = _run(*_base_args(api.base_url), "poll", "vid_1", *options)
                self.assertEqual(result.returncode, 1)

    def test_delete_204_succeeds_and_unsafe_409_fails(self) -> None:
        with _LifecycleServer([(204, {})]) as api:
            result = _run(*_base_args(api.base_url), "delete", "vid_1")
        self.assertEqual(result.returncode, 0, result.stderr)

        error = {"error": {"code": "video_delete_unsafe"}}
        with _LifecycleServer([(409, error)]) as api:
            result = _run(*_base_args(api.base_url), "delete", "vid_1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("video_delete_unsafe", result.stderr)

    def test_download_requires_output_and_missing_auth_is_operational_failure(self) -> None:
        syntax = _run("download", "vid_1", api_key=None)
        self.assertEqual(syntax.returncode, 2)

        with tempfile.TemporaryDirectory() as tmp:
            missing_auth = _run(
                "download", "vid_1", "--output", str(Path(tmp) / "video.mp4"), api_key=None
            )
        self.assertEqual(missing_auth.returncode, 1)
        self.assertIn("Missing API key", missing_auth.stderr)


if __name__ == "__main__":
    unittest.main()
