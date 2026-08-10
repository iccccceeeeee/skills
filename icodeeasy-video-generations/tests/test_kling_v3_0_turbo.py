"""Kling 3.0 Turbo command contract."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _video_common import build_standard_parser, build_standard_payload  # noqa: E402
from kling_v3_0_turbo import MODEL_SPEC  # noqa: E402


class KlingV30TurboTests(unittest.TestCase):
    def test_accepts_three_to_fifteen_seconds_and_first_frame(self) -> None:
        args = build_standard_parser(MODEL_SPEC).parse_args(
            (
                "create",
                "--prompt",
                "A moving train",
                "--resolution",
                "1080p",
                "--duration",
                "3",
                "--first-frame",
                "https://cdn.example/first.png",
            )
        )

        self.assertEqual(
            build_standard_payload(MODEL_SPEC, args),
            {
                "model": "kling-3.0-turbo",
                "prompt": "A moving train",
                "resolution": "1080p",
                "ratio": "adaptive",
                "duration": 3,
                "content": [
                    {
                        "type": "image_url",
                        "image_url": "https://cdn.example/first.png",
                        "role": "first_frame",
                    }
                ],
            },
        )

    def test_rejects_audio_last_frame_and_roleless_references(self) -> None:
        parser = build_standard_parser(MODEL_SPEC)

        for arguments in (
            ("create", "--prompt", "x", "--generate-audio"),
            ("create", "--prompt", "x", "--last-frame", "https://cdn.example/last.png"),
            ("create", "--prompt", "x", "--reference-image", "https://cdn.example/ref.png"),
            ("create", "--prompt", "x", "--duration", "2"),
            ("create", "--prompt", "x", "--duration", "16"),
        ):
            with self.subTest(arguments=arguments), self.assertRaises(SystemExit):
                parser.parse_args(arguments)


if __name__ == "__main__":
    unittest.main()
