"""Kling V3 Omni command contract."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _video_common import build_standard_parser, build_standard_payload  # noqa: E402
from kling_v3_omni import MODEL_SPEC  # noqa: E402


class KlingV3OmniTests(unittest.TestCase):
    def test_roleful_first_last_frames_have_default_audio(self) -> None:
        args = build_standard_parser(MODEL_SPEC).parse_args(
            (
                "create",
                "--prompt",
                "A character turns around",
                "--first-frame",
                "https://cdn.example/first.png",
                "--last-frame",
                "https://cdn.example/last.png",
            )
        )

        payload = build_standard_payload(MODEL_SPEC, args)

        self.assertTrue(payload["generate_audio"])
        self.assertEqual([image["role"] for image in payload["content"]], ["first_frame", "last_frame"])

    def test_accepts_at_most_two_explicit_roleless_references(self) -> None:
        parser = build_standard_parser(MODEL_SPEC)
        args = parser.parse_args(
            (
                "create",
                "--prompt",
                "Use these characters",
                "--reference-image",
                "https://cdn.example/one.png",
                "--reference-image",
                "https://cdn.example/two.png",
            )
        )

        self.assertEqual(
            build_standard_payload(MODEL_SPEC, args)["content"],
            [
                {"type": "image_url", "image_url": "https://cdn.example/one.png"},
                {"type": "image_url", "image_url": "https://cdn.example/two.png"},
            ],
        )
        with self.assertRaises(SystemExit):
            parser.parse_args(
                (
                    "create", "--prompt", "x",
                    "--reference-image", "https://cdn.example/one.png",
                    "--reference-image", "https://cdn.example/two.png",
                    "--reference-image", "https://cdn.example/three.png",
                )
            )

    def test_rejects_mixed_roleful_and_roleless_references(self) -> None:
        parser = build_standard_parser(MODEL_SPEC)

        with self.assertRaises(SystemExit):
            parser.parse_args(
                (
                    "create", "--prompt", "x",
                    "--first-frame", "https://cdn.example/first.png",
                    "--reference-image", "https://cdn.example/reference.png",
                )
            )


if __name__ == "__main__":
    unittest.main()
