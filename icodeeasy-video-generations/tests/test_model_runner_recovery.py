"""CLI recovery-context contracts for standard and Motion Control runners."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


TESTS = Path(__file__).resolve().parent
SCRIPTS = TESTS.parent / "scripts"
sys.path.insert(0, str(TESTS))

from fake_video_api import FakeVideoAPI  # noqa: E402


STANDARD_SCRIPT = SCRIPTS / "doubao_seedance_2_5.py"
MOTION_SCRIPT = SCRIPTS / "kling_v3_motion_control.py"


def _run(script: Path, base_url: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.pop("OPENAI_API_KEY", None)
    environment.pop("ANTHROPIC_AUTH_TOKEN", None)
    environment["OPENAI_API_KEY"] = "test-key"
    return subprocess.run(
        [
            sys.executable,
            str(script),
            "--base-url",
            base_url,
            "--trust-custom-base-url",
            "--allow-insecure-localhost",
            "--json",
            *arguments,
        ],
        text=True,
        capture_output=True,
        env=environment,
        timeout=5,
    )


def _run_human(
    script: Path, base_url: str, *arguments: str
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.pop("OPENAI_API_KEY", None)
    environment.pop("ANTHROPIC_AUTH_TOKEN", None)
    environment["OPENAI_API_KEY"] = "test-key"
    return subprocess.run(
        [
            sys.executable,
            str(script),
            "--base-url",
            base_url,
            "--trust-custom-base-url",
            "--allow-insecure-localhost",
            *arguments,
        ],
        text=True,
        capture_output=True,
        env=environment,
        timeout=5,
    )


def _create_arguments(key: str) -> tuple[str, ...]:
    return ("create", "--confirm-paid", "--idempotency-key", key, "--prompt", "recover")


def _run_arguments(key: str) -> tuple[str, ...]:
    return (
        "run",
        "--confirm-paid",
        "--idempotency-key",
        key,
        "--prompt",
        "recover",
        "--interval",
        "0.01",
        "--max-wait",
        "0.1",
    )


class ModelRunnerRecoveryTests(unittest.TestCase):
    def test_human_create_displays_key_before_standard_or_motion_post(self) -> None:
        cases = (
            (STANDARD_SCRIPT, ()),
            (
                MOTION_SCRIPT,
                (
                    "--reference-image",
                    "https://cdn.example/reference.png",
                    "--reference-video",
                    "https://cdn.example/motion.mp4",
                ),
            ),
        )
        for script, extra_arguments in cases:
            with self.subTest(script=script.name), FakeVideoAPI() as api:
                key = f"idem-{script.stem}-human"
                result = _run_human(
                    script, api.base_url, *_create_arguments(key), *extra_arguments
                )

            self.assertEqual(result.returncode, 0)
            self.assertIn(f"Submitting task with idempotency key: {key}", result.stderr)
            self.assertEqual(len(api.requests), 1)

    def test_standard_accepted_disconnect_reports_idempotency_key_as_one_json_error(self) -> None:
        key = "idem-standard-disconnect"
        with FakeVideoAPI() as api:
            api.disconnect_after_create = True
            result = _run(STANDARD_SCRIPT, api.base_url, *_create_arguments(key))

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout.count("\n"), 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["idempotency_key"], key)
        self.assertIn("error", payload)
        self.assertEqual(len(api.requests), 1)

    def test_motion_accepted_disconnect_reports_idempotency_key_as_one_json_error(self) -> None:
        key = "idem-motion-disconnect"
        with FakeVideoAPI() as api:
            api.disconnect_after_create = True
            result = _run(
                MOTION_SCRIPT,
                api.base_url,
                *_create_arguments(key),
                "--reference-image",
                "https://cdn.example/reference.png",
                "--reference-video",
                "https://cdn.example/motion.mp4",
            )

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout.count("\n"), 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["idempotency_key"], key)
        self.assertIn("error", payload)
        self.assertEqual(len(api.requests), 1)

    def test_standard_poll_failure_retains_accepted_task_and_idempotency_key(self) -> None:
        key = "idem-standard-poll"
        with FakeVideoAPI() as api:
            api.poll_error_status = 503
            result = _run(STANDARD_SCRIPT, api.base_url, *_run_arguments(key))
            task_id = api.tasks[key][1]

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, "")
        payload = json.loads(result.stdout)
        self.assertEqual(payload["idempotency_key"], key)
        self.assertEqual(payload["task_id"], task_id)
        self.assertIn("error", payload)
        self.assertEqual(len(api.requests), 2)

    def test_motion_poll_failure_retains_accepted_task_and_idempotency_key(self) -> None:
        key = "idem-motion-poll"
        with FakeVideoAPI() as api:
            api.poll_error_status = 503
            result = _run(
                MOTION_SCRIPT,
                api.base_url,
                *_run_arguments(key),
                "--reference-image",
                "https://cdn.example/reference.png",
                "--reference-video",
                "https://cdn.example/motion.mp4",
            )
            task_id = api.tasks[key][1]

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, "")
        payload = json.loads(result.stdout)
        self.assertEqual(payload["idempotency_key"], key)
        self.assertEqual(payload["task_id"], task_id)
        self.assertIn("error", payload)
        self.assertEqual(len(api.requests), 2)

    def test_post_create_download_failure_retains_recovery_identifiers(self) -> None:
        cases = (
            (STANDARD_SCRIPT, ()),
            (
                MOTION_SCRIPT,
                (
                    "--reference-image",
                    "https://cdn.example/reference.png",
                    "--reference-video",
                    "https://cdn.example/motion.mp4",
                ),
            ),
        )
        for script, extra_arguments in cases:
            with self.subTest(script=script.name), tempfile.TemporaryDirectory() as tmp:
                key = f"idem-{script.stem}-download"
                with FakeVideoAPI() as api:
                    api.download_error_status = 503
                    result = _run(
                        script,
                        api.base_url,
                        *_run_arguments(key),
                        "--output",
                        str(Path(tmp) / "video.mp4"),
                        *extra_arguments,
                    )
                    task_id = api.tasks[key][1]

                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stderr, "")
                payload = json.loads(result.stdout)
                self.assertEqual(payload["idempotency_key"], key)
                self.assertEqual(payload["task_id"], task_id)
                self.assertIn("error", payload)


if __name__ == "__main__":
    unittest.main()
