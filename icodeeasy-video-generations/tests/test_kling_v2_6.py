"""Kling 2.6 command contract."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _video_common import build_standard_parser, build_standard_payload  # noqa: E402
from kling_v2_6 import MODEL_SPEC  # noqa: E402


def _parse(*arguments: str):
    return build_standard_parser(MODEL_SPEC).parse_args(arguments)


class KlingV26Tests(unittest.TestCase):
    def test_defaults_and_1080p_audio_contract(self) -> None:
        defaults = _parse("create", "--prompt", "A quiet lake")
        audio = _parse(
            "create",
            "--prompt",
            "A concert hall",
            "--resolution",
            "1080p",
            "--duration",
            "10",
            "--generate-audio",
        )

        self.assertEqual(
            build_standard_payload(MODEL_SPEC, defaults),
            {
                "model": "kling-v2-6",
                "prompt": "A quiet lake",
                "resolution": "720p",
                "ratio": "9:16",
                "duration": 5,
                "generate_audio": False,
            },
        )
        self.assertTrue(build_standard_payload(MODEL_SPEC, audio)["generate_audio"])

    def test_last_frame_requires_1080p_and_disables_audio(self) -> None:
        parser = build_standard_parser(MODEL_SPEC)

        for arguments in (
            ("create", "--prompt", "x", "--generate-audio"),
            ("create", "--prompt", "x", "--last-frame", "https://cdn.example/last.png"),
            (
                "create",
                "--prompt",
                "x",
                "--resolution",
                "1080p",
                "--first-frame",
                "https://cdn.example/first.png",
                "--last-frame",
                "https://cdn.example/last.png",
                "--generate-audio",
            ),
        ):
            with self.subTest(arguments=arguments), self.assertRaises(SystemExit):
                parser.parse_args(arguments)

        last_frame = _parse(
            "create",
            "--prompt",
            "x",
            "--resolution",
            "1080p",
            "--first-frame",
            "https://cdn.example/first.png",
            "--last-frame",
            "https://cdn.example/last.png",
        )
        self.assertFalse(build_standard_payload(MODEL_SPEC, last_frame)["generate_audio"])

    def test_rejects_roleless_references_and_unsupported_values(self) -> None:
        parser = build_standard_parser(MODEL_SPEC)

        for arguments in (
            ("create", "--prompt", "x", "--reference-image", "https://cdn.example/ref.png"),
            ("create", "--prompt", "x", "--duration", "6"),
            ("create", "--prompt", "x", "--resolution", "4K"),
        ):
            with self.subTest(arguments=arguments), self.assertRaises(SystemExit):
                parser.parse_args(arguments)


if __name__ == "__main__":
    unittest.main()
