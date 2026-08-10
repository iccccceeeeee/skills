"""Grok Imagine 1.5 Video command contracts."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _video_common import UserError, build_standard_parser, build_standard_payload  # noqa: E402
from grok_imagine_1_5_video import MODEL_SPEC  # noqa: E402


SCRIPT = SCRIPTS / "grok_imagine_1_5_video.py"
SUPPLIER_WIRE_ID = "grok-imagine-1.5-video-apimart"


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


class GrokImagine15VideoTests(unittest.TestCase):
    def test_public_defaults_and_full_grok_range(self) -> None:
        parser = build_standard_parser(MODEL_SPEC)
        defaults = parser.parse_args(("create", "--prompt", "A calm river"))
        maximum = parser.parse_args(
            (
                "create",
                "--prompt",
                "A vibrant market",
                "--resolution",
                "720p",
                "--ratio",
                "3:2",
                "--duration",
                "30",
            )
        )

        self.assertEqual(
            build_standard_payload(MODEL_SPEC, defaults),
            {
                "model": "grok-imagine-1.5-video",
                "prompt": "A calm river",
                "resolution": "480p",
                "ratio": "9:16",
                "duration": 6,
            },
        )
        self.assertEqual(
            (maximum.resolution, maximum.ratio, maximum.duration), ("720p", "3:2", 30)
        )

    def test_accepts_seven_unordered_public_https_reference_images(self) -> None:
        parser = build_standard_parser(MODEL_SPEC)
        arguments = ["create", "--prompt", "Use each reference"]
        for number in range(7):
            arguments.extend(("--reference-image", f"https://cdn.example/{number}.png"))

        payload = build_standard_payload(MODEL_SPEC, parser.parse_args(arguments))

        self.assertEqual(
            payload["content"],
            [
                {"type": "image_url", "image_url": f"https://cdn.example/{number}.png"}
                for number in range(7)
            ],
        )

    def test_rejects_frames_audio_short_duration_and_an_eighth_image(self) -> None:
        parser = build_standard_parser(MODEL_SPEC)
        eight_references = ["create", "--prompt", "x"]
        for number in range(8):
            eight_references.extend(("--reference-image", f"https://cdn.example/{number}.png"))

        invalid_commands = (
            ("create", "--prompt", "x", "--first-frame", "https://cdn.example/first.png"),
            ("create", "--prompt", "x", "--last-frame", "https://cdn.example/last.png"),
            ("create", "--prompt", "x", "--generate-audio"),
            ("create", "--prompt", "x", "--duration", "5"),
        )
        for arguments in invalid_commands:
            with self.subTest(arguments=arguments), self.assertRaises(SystemExit):
                parser.parse_args(arguments)

        with self.assertRaises(UserError):
            build_standard_payload(MODEL_SPEC, parser.parse_args(eight_references))

    def test_public_help_and_dry_run_never_expose_the_supplier_wire_id(self) -> None:
        help_result = _run("--help")
        dry_run = _run("--json", "create", "--dry-run", "--prompt", "Keep the model public")

        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertNotIn(SUPPLIER_WIRE_ID, help_result.stdout)
        self.assertEqual(dry_run.returncode, 0, dry_run.stderr)
        self.assertEqual(json.loads(dry_run.stdout)["model"], "grok-imagine-1.5-video")
        self.assertNotIn(SUPPLIER_WIRE_ID, dry_run.stdout)


if __name__ == "__main__":
    unittest.main()
