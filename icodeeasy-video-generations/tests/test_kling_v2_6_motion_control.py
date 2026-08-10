"""Kling 2.6 Motion Control command contract."""

from __future__ import annotations

import contextlib
import io
import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _video_common import build_motion_parser, build_motion_payload  # noqa: E402
from kling_v2_6_motion_control import MODEL_SPEC, main  # noqa: E402


class KlingV26MotionControlTests(unittest.TestCase):
    def test_defaults_build_the_documented_motion_payload(self) -> None:
        args = build_motion_parser(MODEL_SPEC).parse_args(
            (
                "create",
                "--reference-image",
                "https://cdn.example/reference.png",
                "--reference-video",
                "https://cdn.example/motion.mp4",
            )
        )

        self.assertEqual(
            build_motion_payload(MODEL_SPEC, args),
            {
                "model": "kling-v2-6-motion-control",
                "prompt": "",
                "mode": "std",
                "orientation": "image",
                "keep_original_sound": True,
                "content": [
                    {
                        "type": "image_url",
                        "image_url": "https://cdn.example/reference.png",
                        "role": "reference_image",
                    },
                    {
                        "type": "video_url",
                        "video_url": "https://cdn.example/motion.mp4",
                        "role": "reference_video",
                    },
                ],
            },
        )

    def test_accepts_all_motion_options_without_media_probing(self) -> None:
        args = build_motion_parser(MODEL_SPEC).parse_args(
            (
                "create",
                "--prompt",
                "Match the dancer's movement",
                "--mode",
                "pro",
                "--orientation",
                "video",
                "--no-keep-original-sound",
                "--reference-image",
                "https://cdn.example/reference.png",
                "--reference-video",
                "https://cdn.example/motion.mp4",
            )
        )

        payload = build_motion_payload(MODEL_SPEC, args)
        self.assertEqual(payload["model"], "kling-v2-6-motion-control")
        self.assertEqual((payload["mode"], payload["orientation"]), ("pro", "video"))
        self.assertFalse(payload["keep_original_sound"])
        self.assertEqual(payload["prompt"], "Match the dancer's movement")

    def test_requires_one_https_image_and_one_https_video(self) -> None:
        parser = build_motion_parser(MODEL_SPEC)

        for arguments in (
            ("create", "--reference-video", "https://cdn.example/motion.mp4"),
            ("create", "--reference-image", "https://cdn.example/reference.png"),
            (
                "create",
                "--reference-image",
                "http://cdn.example/reference.png",
                "--reference-video",
                "https://cdn.example/motion.mp4",
            ),
            (
                "create",
                "--reference-image",
                "https://cdn.example/reference.png",
                "--reference-video",
                "http://cdn.example/motion.mp4",
            ),
        ):
            with self.subTest(arguments=arguments), self.assertRaises(SystemExit):
                parser.parse_args(arguments)

    def test_rejects_standard_video_options(self) -> None:
        parser = build_motion_parser(MODEL_SPEC)
        required = (
            "--reference-image",
            "https://cdn.example/reference.png",
            "--reference-video",
            "https://cdn.example/motion.mp4",
        )

        for unsupported in (
            ("--resolution", "1080p"),
            ("--ratio", "16:9"),
            ("--duration", "5"),
            ("--generate-audio",),
            ("--first-frame", "https://cdn.example/first.png"),
            ("--last-frame", "https://cdn.example/last.png"),
        ):
            with self.subTest(unsupported=unsupported), self.assertRaises(SystemExit):
                parser.parse_args(("create", *required, *unsupported))

    def test_prompt_file_error_does_not_disclose_its_local_path(self) -> None:
        separator = "/"
        private_username = "private" + "-" + "user"
        private_path = separator.join(
            ("", "Users", private_username, "secret-prompts", "motion.txt")
        )
        stderr = io.StringIO()

        with contextlib.redirect_stderr(stderr):
            exit_code = main(
                (
                    "create",
                    "--prompt-file",
                    private_path,
                    "--reference-image",
                    "https://cdn.example/reference.png",
                    "--reference-video",
                    "https://cdn.example/motion.mp4",
                )
            )

        self.assertEqual(exit_code, 1)
        self.assertIn("Could not read prompt file.", stderr.getvalue())
        self.assertNotIn(private_path, stderr.getvalue())
        self.assertNotIn(private_username, stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
