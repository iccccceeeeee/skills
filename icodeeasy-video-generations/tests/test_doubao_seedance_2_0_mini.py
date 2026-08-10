"""Seedance 2.0 Mini command contracts."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _video_common import build_standard_parser, build_standard_payload  # noqa: E402
from doubao_seedance_2_0_mini import MODEL_SPEC  # noqa: E402


class Seedance20MiniTests(unittest.TestCase):
    def test_rejects_data_urls_and_last_frame_without_first_frame(self) -> None:
        parser = build_standard_parser(MODEL_SPEC)
        for arguments in (
            ("create", "--prompt", "x", "--first-frame", "data:image/png;base64,AAAA"),
            ("create", "--prompt", "x", "--last-frame", "https://cdn.example/last.png"),
        ):
            with self.subTest(arguments=arguments), self.assertRaises(SystemExit):
                parser.parse_args(arguments)

    def test_accepts_only_480p_or_720p_for_four_to_fifteen_seconds(self) -> None:
        args = build_standard_parser(MODEL_SPEC).parse_args(
            ("create", "--prompt", "A small robot", "--resolution", "720p", "--duration", "15")
        )

        self.assertEqual((args.resolution, args.duration), ("720p", 15))

    def test_rejects_unsupported_audio_and_out_of_range_generation_options(self) -> None:
        parser = build_standard_parser(MODEL_SPEC)
        for arguments in (
            ("create", "--prompt", "x", "--resolution", "1080p"),
            ("create", "--prompt", "x", "--duration", "3"),
            ("create", "--prompt", "x", "--duration", "16"),
            ("create", "--prompt", "x", "--generate-audio"),
        ):
            with self.subTest(arguments=arguments), self.assertRaises(SystemExit):
                parser.parse_args(arguments)

    def test_valid_payload_omits_generate_audio(self) -> None:
        args = build_standard_parser(MODEL_SPEC).parse_args(
            ("create", "--prompt", "A small robot", "--resolution", "480p")
        )

        payload = build_standard_payload(MODEL_SPEC, args)

        self.assertNotIn("generate_audio", payload)


if __name__ == "__main__":
    unittest.main()
