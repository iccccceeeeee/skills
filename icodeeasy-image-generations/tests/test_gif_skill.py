"""GIF-specific request and recovery behavior for the Image 2.6 skill."""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_generate_image import FakeAPI

SCRIPT = Path(__file__).resolve().parents[2] / "image26-icodeeasy/scripts/generate_image.py"
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
        return image.build_payload(args, require_reference=False)

    def test_gif_defaults_match_the_verified_provider_contract(self):
        payload = self.payload("--format", "gif")
        self.assertEqual(payload["output_format"], "gif")
        self.assertEqual(payload["frame_count"], 9)
        self.assertEqual(payload["frame_duration_ms"], 200)
        self.assertEqual(payload["size"], "auto")
        self.assertEqual(payload["n"], 1)
        self.assertNotIn("image_size", payload)
        self.assertNotIn("resolution", payload)

    def test_custom_gif_frames_and_size_are_forwarded(self):
        payload = self.payload("--format", "gif", "--frame-count", "4",
                               "--frame-duration-ms", "300", "--frame-size", "768x432")
        self.assertEqual(payload["frame_count"], 4)
        self.assertEqual(payload["frame_duration_ms"], 300)
        self.assertEqual(payload["size"], "768x432")

    def test_unsupported_gif_inputs_fail_before_submission(self):
        invalid = [
            ("--frame-count", "1"), ("--frame-count", "17"),
            ("--frame-duration-ms", "10"), ("--frame-duration-ms", "205"),
            ("--frame-size", "1024x1024"), ("--frame-size", "513x512"),
            ("--frame-size", f"{16 * 10**400}x512"),
            ("--frame-size", "16:9"), ("--resolution", "2k"),
            ("--aspect-ratio", "16:9"), ("--image-url", "https://example.test/ref.png"),
        ]
        for options in invalid:
            with self.subTest(options=options), self.assertRaises(image.UserError):
                self.payload("--format", "gif", *options)

    def test_frame_options_require_gif_output(self):
        with self.assertRaises(image.UserError):
            self.payload("--frame-count", "9")

    def test_gif_result_keeps_its_file_extension_and_uses_one_task(self):
        gif_bytes = b"GIF89a" + bytes.fromhex("01000100800000000000ffffff3b")
        with tempfile.TemporaryDirectory() as directory:
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
                        "generate", "--prompt", "A swaying lantern", "--format", "gif",
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
            self.assertEqual(api.requests[0][2]["output_format"], "gif")


if __name__ == "__main__":
    unittest.main()
