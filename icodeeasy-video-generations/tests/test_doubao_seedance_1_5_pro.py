"""Seedance 1.5 Pro command contracts."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _video_common import build_standard_parser, build_standard_payload  # noqa: E402
from doubao_seedance_1_5_pro import MODEL_SPEC  # noqa: E402


class Seedance15ProTests(unittest.TestCase):
    def test_supports_1080p_for_up_to_twelve_seconds_without_adaptive_ratio(self) -> None:
        args = build_standard_parser(MODEL_SPEC).parse_args(
            ("create", "--prompt", "A bright studio", "--resolution", "1080p", "--ratio", "16:9", "--duration", "12")
        )

        payload = build_standard_payload(MODEL_SPEC, args)

        self.assertEqual((payload["resolution"], payload["ratio"], payload["duration"]), ("1080p", "16:9", 12))

    def test_rejects_4k_adaptive_ratio_and_duration_above_twelve_seconds(self) -> None:
        parser = build_standard_parser(MODEL_SPEC)
        for arguments in (
            ("create", "--prompt", "x", "--resolution", "4K"),
            ("create", "--prompt", "x", "--ratio", "adaptive"),
            ("create", "--prompt", "x", "--duration", "13"),
        ):
            with self.subTest(arguments=arguments), self.assertRaises(SystemExit):
                parser.parse_args(arguments)

    def test_rejects_unsupported_frame_and_reference_options(self) -> None:
        parser = build_standard_parser(MODEL_SPEC)
        for arguments in (
            ("create", "--prompt", "x", "--first-frame", "https://cdn.example/first.png"),
            ("create", "--prompt", "x", "--last-frame", "https://cdn.example/last.png"),
            ("create", "--prompt", "x", "--reference-image", "https://cdn.example/reference.png"),
        ):
            with self.subTest(arguments=arguments), self.assertRaises(SystemExit):
                parser.parse_args(arguments)

    def test_standard_payload_omits_content(self) -> None:
        args = build_standard_parser(MODEL_SPEC).parse_args(
            ("create", "--prompt", "A bright studio")
        )

        payload = build_standard_payload(MODEL_SPEC, args)

        self.assertNotIn("content", payload)


if __name__ == "__main__":
    unittest.main()
