"""MiniMax H3 command contracts."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _video_common import build_standard_parser, build_standard_payload  # noqa: E402
from minimax_h3 import MODEL_SPEC  # noqa: E402


SCRIPT = SCRIPTS / "minimax_h3.py"


def _run(*arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.pop("OPENAI_API_KEY", None)
    environment.pop("ANTHROPIC_AUTH_TOKEN", None)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *arguments],
        text=True,
        capture_output=True,
        env=environment,
        timeout=5,
    )


class MiniMaxH3Tests(unittest.TestCase):
    def test_defaults_and_supported_2k_h3_contract(self) -> None:
        parser = build_standard_parser(MODEL_SPEC)
        defaults = parser.parse_args(("create", "--prompt", "A mountain lake"))
        two_k = parser.parse_args(
            (
                "create",
                "--prompt",
                "A detailed cityscape",
                "--resolution",
                "2K",
                "--ratio",
                "21:9",
                "--duration",
                "15",
            )
        )

        self.assertEqual(
            build_standard_payload(MODEL_SPEC, defaults),
            {
                "model": "MiniMax-H3",
                "prompt": "A mountain lake",
                "resolution": "768P",
                "ratio": "9:16",
                "duration": 5,
            },
        )
        self.assertEqual(
            (two_k.resolution, two_k.ratio, two_k.duration), ("2K", "21:9", 15)
        )

    def test_first_and_last_frames_keep_their_public_roles(self) -> None:
        args = build_standard_parser(MODEL_SPEC).parse_args(
            (
                "create",
                "--prompt",
                "Match the opening and ending shots",
                "--first-frame",
                "https://cdn.example/first.png",
                "--last-frame",
                "https://cdn.example/last.png",
            )
        )

        payload = build_standard_payload(MODEL_SPEC, args)

        self.assertEqual(
            payload["content"],
            [
                {
                    "type": "image_url",
                    "image_url": "https://cdn.example/first.png",
                    "role": "first_frame",
                },
                {
                    "type": "image_url",
                    "image_url": "https://cdn.example/last.png",
                    "role": "last_frame",
                },
            ],
        )

    def test_rejects_case_changed_resolution_and_out_of_range_duration(self) -> None:
        parser = build_standard_parser(MODEL_SPEC)

        for arguments in (
            ("create", "--prompt", "x", "--resolution", "2k"),
            ("create", "--prompt", "x", "--duration", "3"),
            ("create", "--prompt", "x", "--duration", "16"),
        ):
            with self.subTest(arguments=arguments), self.assertRaises(SystemExit):
                parser.parse_args(arguments)

    def test_public_surface_has_no_generated_audio_option_or_payload_field(self) -> None:
        result = _run("--help")
        dry_run = _run("--json", "create", "--dry-run", "--prompt", "Silent scene")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("generate-audio", result.stdout)
        self.assertEqual(dry_run.returncode, 0, dry_run.stderr)
        self.assertNotIn("generate_audio", json.loads(dry_run.stdout))


if __name__ == "__main__":
    unittest.main()
