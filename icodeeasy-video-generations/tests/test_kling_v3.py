"""Kling V3 command contract."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _video_common import build_standard_parser, build_standard_payload  # noqa: E402
from kling_v3 import MODEL_SPEC  # noqa: E402


class KlingV3Tests(unittest.TestCase):
    def test_default_audio_and_4k_first_last_contract(self) -> None:
        parser = build_standard_parser(MODEL_SPEC)
        defaults = parser.parse_args(("create", "--prompt", "A quiet lake"))
        frames = parser.parse_args(
            (
                "create",
                "--prompt",
                "A travelling shot",
                "--resolution",
                "4K",
                "--duration",
                "15",
                "--first-frame",
                "https://cdn.example/first.png",
                "--last-frame",
                "https://cdn.example/last.png",
            )
        )

        self.assertTrue(build_standard_payload(MODEL_SPEC, defaults)["generate_audio"])
        payload = build_standard_payload(MODEL_SPEC, frames)
        self.assertEqual((payload["resolution"], payload["duration"], payload["ratio"]), ("4K", 15, "adaptive"))
        self.assertEqual([image["role"] for image in payload["content"]], ["first_frame", "last_frame"])

    def test_rejects_roleless_references_last_only_and_out_of_range_duration(self) -> None:
        parser = build_standard_parser(MODEL_SPEC)

        for arguments in (
            ("create", "--prompt", "x", "--reference-image", "https://cdn.example/ref.png"),
            ("create", "--prompt", "x", "--last-frame", "https://cdn.example/last.png"),
            ("create", "--prompt", "x", "--duration", "2"),
            ("create", "--prompt", "x", "--duration", "16"),
        ):
            with self.subTest(arguments=arguments), self.assertRaises(SystemExit):
                parser.parse_args(arguments)


if __name__ == "__main__":
    unittest.main()
