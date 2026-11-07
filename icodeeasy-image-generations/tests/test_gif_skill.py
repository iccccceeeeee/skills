"""GIF-specific request and recovery behavior for the Image 2.6 skill."""

import base64
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

from test_generate_image import FakeAPI

SCRIPT = Path(__file__).resolve().parents[2] / "image26-gif-icodeeasy/scripts/generate_image.py"
spec = importlib.util.spec_from_file_location("image26_gif", SCRIPT)
image = importlib.util.module_from_spec(spec)
spec.loader.exec_module(image)


class GifSkillTests(unittest.TestCase):
    def payload(self, *options):
        try:
            args = image.build_parser().parse_args([
                "generate", "--prompt", "A paper lantern swaying gently", *options,
            ])
        except SystemExit:
            self.fail("The Image 2.6 CLI does not accept the requested GIF options")
        return image.build_payload(args)

    def test_gif_defaults_match_the_verified_provider_contract(self):
        payload = self.payload()
        self.assertEqual(payload["output_format"], "gif")
        self.assertNotIn("frame_count", payload)
        self.assertNotIn("frame_duration_ms", payload)
        self.assertEqual(payload["size"], "auto")
        self.assertEqual(payload["n"], 1)
        self.assertEqual(payload["model"], "gpt-image-2.6-flare")
        self.assertEqual(self.payload("--model", "gpt-image-2.6-sunburst")["model"], "gpt-image-2.6-sunburst")
        self.assertNotIn("image_size", payload)
        self.assertNotIn("resolution", payload)
        self.assertNotIn("image_urls", payload)

    def test_legacy_gif_defaults_are_accepted_without_forwarding(self):
        for size in ("auto", "512x512"):
            with self.subTest(size=size):
                self.assertEqual(self.payload("--frame-count", "9", "--frame-duration-ms", "200",
                                              "--frame-size", size), self.payload())

    def test_unsupported_gif_inputs_fail_before_submission(self):
        invalid = [
            ("--n", "2"),
            ("--frame-count", "4"),
            ("--frame-duration-ms", "300"),
            ("--frame-size", "768x432"),
        ]
        for options in invalid:
            with self.subTest(options=options), self.assertRaises(image.UserError):
                self.payload(*options)

    def test_static_options_and_insecure_references_are_rejected_before_submission(self):
        for options in (("--format", "png"), ("--resolution", "2k"),
                        ("--aspect-ratio", "16:9"), ("--image-url", "http://example.test/ref.png")):
            with self.subTest(options=options), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                image.main(["generate", "--prompt", "A lantern", "--dry-run", *options])
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            image.main(["edit", "--prompt", "Animate a lantern", "--dry-run"])

    def test_reference_limit_counts_urls_and_files_together(self):
        with tempfile.TemporaryDirectory() as directory:
            ref = Path(directory) / "ref.png"
            ref.write_bytes(b"test image")
            options = ["--image-url", "https://example.test/ref.png"] * 7
            options += ["--image-file", str(ref)]
            self.assertEqual(len(self.payload(*options)["image_urls"]), 8)
            with self.assertRaisesRegex(image.UserError, "at most 8"):
                self.payload(*options, "--image-file", str(ref))
            with self.assertRaisesRegex(image.UserError, "not found"):
                self.payload("--image-file", str(Path(directory) / "missing.png"))

    def test_gif_skill_runs_with_only_its_own_installed_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "image26-gif-icodeeasy"
            shutil.copytree(SCRIPT.parents[1], target)
            ref = Path(directory) / "ref.png"
            ref.write_bytes(b"test image")
            result = subprocess.run([
                sys.executable, str(target / "scripts/generate_image.py"),
                "generate", "--prompt", "A lantern",
                "--image-url", "https://example.test/ref.png",
                "--image-url", "data:image/png;base64,aW1hZ2U=",
                "--image-file", str(ref), "--dry-run", "--json",
            ], cwd=directory, capture_output=True, text=True, check=True,
               env={key: value for key, value in os.environ.items()
                    if key not in ("OPENAI_API_KEY", "ANTHROPIC_AUTH_TOKEN", "PYTHONPATH")})
        payload = json.loads(result.stdout)["payload"]
        self.assertEqual(payload["output_format"], "gif")
        self.assertEqual(payload["image_urls"], ["https://example.test/ref.png", "<data-url>", "<data-url>"])

    def test_gif_result_keeps_its_file_extension_and_uses_one_task(self):
        gif_bytes = b"GIF89a" + bytes.fromhex("01000100800000000000ffffff3b")
        with tempfile.TemporaryDirectory() as directory:
            first_ref = Path(directory) / "first.png"
            second_ref = Path(directory) / "second.jpg"
            first_ref.write_bytes(b"first image")
            second_ref.write_bytes(b"second image")
            with FakeAPI([
                (202, {"status": "pending", "task_id": "gif-task"}),
                (200, {"status": "submitted", "task_id": "gif-task"}),
                (200, lambda base: {"status": "completed", "task_id": "gif-task",
                                   "result_url": base + "/animation.gif"}),
                (200, gif_bytes),
            ]) as api:
                output = io.StringIO()
                with patch.dict(os.environ, {"OPENAI_API_KEY": "gif-test-key"}, clear=True), contextlib.redirect_stdout(output):
                    code = image.main([
                        "generate", "--prompt", "A swaying lantern",
                        "--image-url", "https://example.test/first.png",
                        "--image-url", "https://example.test/second.png",
                        "--image-file", str(first_ref), "--image-file", str(second_ref),
                        "--async", "--wait", "--poll-interval", "0", "--base-url", api.base_url,
                        "--download-dir", directory, "--json",
                    ])
            result = json.loads(output.getvalue())
            self.assertEqual(code, 0, result)
            saved = Path(result["downloads"][0])
            self.assertEqual(saved.suffix, ".gif")
            self.assertEqual(saved.read_bytes(), gif_bytes)
            self.assertEqual(result["task_id"], "gif-task")
            self.assertEqual([request[0] for request in api.requests], ["POST", "GET", "GET", "GET"])
            _, endpoint, payload = api.requests[0]
            self.assertEqual(endpoint, "/v1/images/generations?async=1")
            self.assertEqual(payload["output_format"], "gif")
            self.assertEqual(payload["size"], "auto")
            self.assertEqual(payload["image_urls"], [
                "https://example.test/first.png", "https://example.test/second.png",
                "data:image/png;base64," + base64.b64encode(b"first image").decode("ascii"),
                "data:image/jpeg;base64," + base64.b64encode(b"second image").decode("ascii"),
            ])

    def test_download_failure_can_resume_the_same_gif_task(self):
        gif_bytes = b"GIF89a" + bytes.fromhex("01000100800000000000ffffff3b")
        completed = lambda base: {"status": "completed", "task_id": "recover-gif",
                                  "result_url": base + "/animation.gif"}
        with tempfile.TemporaryDirectory() as directory, FakeAPI([
            (202, {"status": "pending", "task_id": "recover-gif"}),
            (200, completed),
            (503, {"error": {"message": "Temporary download failure"}}),
            (200, completed),
            (200, gif_bytes),
        ]) as api, patch.dict(os.environ, {"OPENAI_API_KEY": "gif-test-key"}, clear=True):
            failed = io.StringIO()
            common = ["--base-url", api.base_url, "--download-dir", directory, "--json"]
            with contextlib.redirect_stdout(failed):
                code = image.main(["generate", "--prompt", "A lantern", "--async", "--wait", *common])
            failure = json.loads(failed.getvalue())
            self.assertEqual(code, 1)
            self.assertEqual(failure["task_id"], "recover-gif")
            self.assertIn("poll", failure["resume_command"])
            self.assertIn("image26-gif-icodeeasy", " ".join(failure["resume_command"]))
            recovered = io.StringIO()
            with contextlib.redirect_stdout(recovered):
                code = image.main(["poll", "recover-gif", "--wait", *common])
            result = json.loads(recovered.getvalue())
            self.assertEqual(code, 0, result)
            self.assertEqual(Path(result["downloads"][0]).read_bytes(), gif_bytes)
            self.assertEqual([request[0] for request in api.requests], ["POST", "GET", "GET", "GET", "GET"])
            self.assertNotIn("gif-test-key", failed.getvalue() + recovered.getvalue())

    def test_png_response_is_recoverable_without_writing_or_resubmitting(self):
        with tempfile.TemporaryDirectory() as directory, FakeAPI([
            (200, lambda base: {"status": "completed", "task_id": "wrong-format",
                               "result_url": base + "/animation.gif"}),
            (200, b"\x89PNG\r\n\x1a\n" + b"not-a-gif"),
        ]) as api, patch.dict(os.environ, {"OPENAI_API_KEY": "gif-test-key"}, clear=True):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = image.main(["generate", "--prompt", "A lantern", "--base-url", api.base_url,
                                   "--download-dir", directory, "--json"])
            result = json.loads(output.getvalue())
            self.assertEqual(code, 1, result)
            self.assertFalse(result["ok"])
            self.assertEqual(result["task_id"], "wrong-format")
            self.assertEqual(result["urls"], [api.base_url + "/animation.gif"])
            self.assertIn("poll", result["resume_command"])
            self.assertEqual(list(Path(directory).iterdir()), [])
            self.assertEqual([request[0] for request in api.requests], ["POST", "GET"])

    def test_gif_bytes_determine_the_download_extension(self):
        gif_bytes = b"GIF89a" + bytes.fromhex("01000100800000000000ffffff3b")
        with tempfile.TemporaryDirectory() as directory, FakeAPI([
            (200, lambda base: {"status": "completed", "task_id": "real-gif",
                               "result_url": base + "/misnamed.png"}),
            (200, gif_bytes),
        ]) as api, patch.dict(os.environ, {"OPENAI_API_KEY": "gif-test-key"}, clear=True):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = image.main(["generate", "--prompt", "A lantern", "--base-url", api.base_url,
                                   "--download-dir", directory, "--json"])
            result = json.loads(output.getvalue())
            self.assertEqual(code, 0, result)
            self.assertEqual(Path(result["downloads"][0]).suffix, ".gif")
            self.assertEqual(Path(result["downloads"][0]).read_bytes(), gif_bytes)

    def test_known_static_result_url_is_not_reported_as_gif_success(self):
        with FakeAPI([
            (200, lambda base: {"status": "completed", "task_id": "static-result",
                               "result_url": base + "/result.png"}),
        ]) as api, patch.dict(os.environ, {"OPENAI_API_KEY": "gif-test-key"}, clear=True):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = image.main(["generate", "--prompt", "A lantern", "--base-url", api.base_url, "--json"])
            result = json.loads(output.getvalue())
            self.assertEqual(code, 1, result)
            self.assertEqual(result["task_id"], "static-result")
            self.assertEqual([request[0] for request in api.requests], ["POST"])


if __name__ == "__main__":
    unittest.main()
