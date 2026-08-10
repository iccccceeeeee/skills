"""Seedance 2.0 Fast command contracts."""

from __future__ import annotations

import unittest
from pathlib import Path
import sys


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _video_common import build_standard_parser, build_standard_payload  # noqa: E402
from doubao_seedance_2_0_fast import MODEL_SPEC  # noqa: E402


class Seedance20FastTests(unittest.TestCase):
    def test_reference_images_have_explicit_reference_role(self) -> None:
        args = build_standard_parser(MODEL_SPEC).parse_args(
            (
                "create", "--prompt", "Match this subject", "--reference-image",
                "https://cdn.example/reference.png",
            )
        )

        payload = build_standard_payload(MODEL_SPEC, args)

        self.assertEqual(payload["content"], [{
            "type": "image_url",
            "image_url": "https://cdn.example/reference.png",
            "role": "reference_image",
        }])

    def test_rejects_1080p_and_duration_above_fifteen_seconds(self) -> None:
        parser = build_standard_parser(MODEL_SPEC)
        for arguments in (
            ("create", "--prompt", "x", "--resolution", "1080p"),
            ("create", "--prompt", "x", "--duration", "16"),
        ):
            with self.subTest(arguments=arguments), self.assertRaises(SystemExit):
                parser.parse_args(arguments)


if __name__ == "__main__":
    unittest.main()
