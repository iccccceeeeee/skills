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
from test_video_task_cli import _run as run_existing_task, _base_args


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

    def test_accepted_truncated_or_invalid_create_remains_submission_unknown(self) -> None:
        cases = (
            (STANDARD_SCRIPT, ()),
            (MOTION_SCRIPT, ("--reference-image", "https://cdn.example/reference.png", "--reference-video", "https://cdn.example/motion.mp4")),
        )
        for script, extra in cases:
            for failure in ("truncate_create_response", "invalid_create_response", "invalid_http_status_after_create"):
                with self.subTest(script=script.name, failure=failure), FakeVideoAPI() as api:
                    setattr(api, failure, True)
                    result = _run(script, api.base_url, *_create_arguments("idem-uncertain"), *extra)
                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(result.stderr, "")
                    payload = json.loads(result.stdout)
                    self.assertEqual(payload["idempotency_key"], "idem-uncertain")
                    self.assertEqual(payload["error"]["stage"], "submission")
                    self.assertTrue(payload["error"]["uncertain"])
                    self.assertEqual(payload["recovery_action"], "reuse_idempotency_key")
                    self.assertNotEqual(payload.get("status"), "failed")
                    self.assertEqual(api.created_task_count, 1)
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

    def test_truncated_http_errors_keep_submission_or_task_recovery_context(self) -> None:
        for stage in ("submission", "poll", "download"):
            with self.subTest(stage=stage), FakeVideoAPI() as api, tempfile.TemporaryDirectory() as tmp:
                api.truncate_error_response = True
                setattr(api, {"submission": "create_error_status", "poll": "poll_error_status", "download": "download_error_status"}[stage], 503)
                arguments = _create_arguments("idem-truncated-error") if stage == "submission" else _run_arguments("idem-truncated-error")
                if stage == "download":
                    arguments += ("--output", str(Path(tmp) / "video.mp4"))
                result = _run(STANDARD_SCRIPT, api.base_url, *arguments)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stderr, "")
                payload = json.loads(result.stdout)
                self.assertEqual(payload["error"]["http_status"], 503)
                self.assertEqual(payload["error"]["stage"], stage)
                self.assertEqual(payload["idempotency_key"], "idem-truncated-error")
                self.assertEqual(payload["recovery_action"], "reuse_idempotency_key" if stage == "submission" else stage)
                if stage == "submission":
                    self.assertTrue(payload["error"]["uncertain"])
                else:
                    self.assertEqual(payload["task_id"], api.tasks["idem-truncated-error"][1])
                    self.assertEqual(payload["status"], "succeeded" if stage == "download" else "queued")
                self.assertEqual(api.created_task_count, 1)
                self.assertEqual(sum(r["method"] == "POST" for r in api.requests), 1)

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

    def test_poll_404_is_unconfirmed_status_and_recovers_without_another_create(self) -> None:
        cases = (
            (STANDARD_SCRIPT, ()),
            (MOTION_SCRIPT, ("--reference-image", "https://cdn.example/reference.png", "--reference-video", "https://cdn.example/motion.mp4")),
        )
        for script, extra in cases:
            with self.subTest(script=script.name), FakeVideoAPI() as api:
                key = "idem-poll-404"
                api.poll_error_status = 404
                result = _run(script, api.base_url, *_run_arguments(key), *extra)
                payload = json.loads(result.stdout)
                task_id = api.tasks[key][1]
                self.assertEqual(result.returncode, 1)
                self.assertEqual(payload["task_id"], task_id)
                self.assertEqual(payload["status"], "queued")
                self.assertEqual(payload["error"]["stage"], "poll")
                self.assertEqual(payload["error"]["http_status"], 404)
                self.assertEqual(payload["recovery_action"], "poll")
                self.assertIn("could not be confirmed", payload["summary"])
                api.poll_error_status = None
                recovered = run_existing_task(*_base_args(api.base_url), "poll", task_id)
                self.assertEqual(recovered.returncode, 0, recovered.stderr)
                self.assertEqual(json.loads(recovered.stdout)["status"], "succeeded")
                self.assertEqual(api.created_task_count, 1)
                self.assertEqual(sum(r["method"] == "POST" for r in api.requests), 1)

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
                    payload = json.loads(result.stdout)
                    self.assertEqual(payload["status"], "succeeded")
                    self.assertEqual(payload["error"]["stage"], "download")
                    self.assertEqual(payload["recovery_action"], "download")
                    self.assertIn("generation succeeded", payload["summary"])
                    api.download_error_status = None
                    output = Path(tmp) / "recovered.mp4"
                    recovered = run_existing_task(*_base_args(api.base_url), "download", task_id, "--output", str(output))
                    self.assertEqual(recovered.returncode, 0, recovered.stderr)
                    self.assertTrue(output.read_bytes().startswith(b"\x00\x00\x00\x18ftyp"))
                    self.assertEqual(api.created_task_count, 1)
                    self.assertEqual(sum(r["method"] == "POST" for r in api.requests), 1)

                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stderr, "")
                payload = json.loads(result.stdout)
                self.assertEqual(payload["idempotency_key"], key)
                self.assertEqual(payload["task_id"], task_id)
                self.assertIn("error", payload)


if __name__ == "__main__":
    unittest.main()
