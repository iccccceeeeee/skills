"""Kling Video O1 command contract."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _video_common import build_standard_parser, build_standard_payload  # noqa: E402
from kling_video_o1 import MODEL_SPEC  # noqa: E402


class KlingVideoO1Tests(unittest.TestCase):
    def test_accepts_five_or_ten_seconds_with_roleful_frames(self) -> None:
        args = build_standard_parser(MODEL_SPEC).parse_args(
            (
                "create", "--prompt", "A theatre curtain rises", "--duration", "10",
                "--first-frame", "https://cdn.example/first.png",
                "--last-frame", "https://cdn.example/last.png",
            )
        )

        payload = build_standard_payload(MODEL_SPEC, args)

        self.assertEqual((payload["model"], payload["duration"], payload["ratio"]), ("kling-video-o1", 10, "adaptive"))
        self.assertEqual([image["role"] for image in payload["content"]], ["first_frame", "last_frame"])

    def test_rejects_audio_roleless_references_last_only_and_other_durations(self) -> None:
        parser = build_standard_parser(MODEL_SPEC)

        for arguments in (
            ("create", "--prompt", "x", "--generate-audio"),
            ("create", "--prompt", "x", "--reference-image", "https://cdn.example/ref.png"),
            ("create", "--prompt", "x", "--last-frame", "https://cdn.example/last.png"),
            ("create", "--prompt", "x", "--duration", "6"),
        ):
            with self.subTest(arguments=arguments), self.assertRaises(SystemExit):
                parser.parse_args(arguments)


if __name__ == "__main__":
    unittest.main()
