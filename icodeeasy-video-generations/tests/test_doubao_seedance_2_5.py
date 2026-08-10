"""Seedance 2.5 command contracts."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _video_common import (  # noqa: E402
    StandardModelSpec,
    build_standard_parser,
    build_standard_payload,
)
from doubao_seedance_2_5 import MODEL_SPEC  # noqa: E402


SCRIPT = SCRIPTS / "doubao_seedance_2_5.py"


def _parse(*arguments: str):
    return build_standard_parser(MODEL_SPEC).parse_args(arguments)


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


class Seedance25Tests(unittest.TestCase):
    def test_defaults_build_the_public_seedance_payload(self) -> None:
        args = _parse("create", "--prompt", "A quiet mountain lake")

        self.assertEqual(
            build_standard_payload(MODEL_SPEC, args),
            {
                "model": "doubao-seedance-2.5",
                "prompt": "A quiet mountain lake",
                "resolution": "480p",
                "ratio": "9:16",
                "duration": 4,
                "generate_audio": True,
            },
        )

    def test_720p_and_30_seconds_are_accepted(self) -> None:
        args = _parse(
            "create",
            "--prompt",
            "A city at dawn",
            "--resolution",
            "720p",
            "--duration",
            "30",
        )

        payload = build_standard_payload(MODEL_SPEC, args)

        self.assertEqual(payload["resolution"], "720p")
        self.assertEqual(payload["duration"], 30)

    def test_first_and_last_frames_have_roles_and_force_adaptive_ratio(self) -> None:
        args = _parse(
            "create",
            "--prompt",
            "Move naturally between frames",
            "--ratio",
            "16:9",
            "--first-frame",
            "https://cdn.example/first.png",
            "--last-frame",
            "https://cdn.example/last.png",
        )

        payload = build_standard_payload(MODEL_SPEC, args)

        self.assertEqual(payload["ratio"], "adaptive")
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

    def test_rejects_unsupported_or_invalid_frame_options(self) -> None:
        invalid_commands = (
            ("create", "--prompt", "x", "--resolution", "1080p"),
            ("create", "--prompt", "x", "--duration", "31"),
            ("create", "--prompt", "x", "--last-frame", "https://cdn.example/last.png"),
            ("create", "--prompt", "x", "--reference-image", "https://cdn.example/reference.png"),
            ("create", "--prompt", "x", "--first-frame", "data:image/png;base64,AAAA"),
            ("create", "--prompt", "x", "--callback", "https://hooks.example/video"),
        )

        for command in invalid_commands:
            with self.subTest(command=command), self.assertRaises(SystemExit):
                _parse(*command)

    def test_rejects_non_public_first_and_last_frame_urls(self) -> None:
        invalid_commands = (
            ("create", "--prompt", "x", "--first-frame", "https://127.0.0.1/image.png"),
            ("create", "--prompt", "x", "--first-frame", "https://localhost/image.png"),
            (
                "create",
                "--prompt",
                "x",
                "--first-frame",
                "https://cdn.example/first.png",
                "--last-frame",
                "https://10.0.0.1/last.png",
            ),
            (
                "create",
                "--prompt",
                "x",
                "--first-frame",
                "https://cdn.example/first.png",
                "--last-frame",
                "https://metadata.local/last.png",
            ),
        )

        for command in invalid_commands:
            with self.subTest(command=command), self.assertRaises(SystemExit):
                _parse(*command)

    def test_accepts_a_globally_routable_ipv6_first_frame_url(self) -> None:
        url = "https://[2001:4860:4860::8888]/image.png"

        args = _parse("create", "--prompt", "x", "--first-frame", url)

        self.assertEqual(args.first_frame, url)

    def test_roleful_generic_reference_spec_emits_reference_image_role(self) -> None:
        roleful_spec = StandardModelSpec(
            canonical_id="test-roleful-reference",
            resolution_choices=("480p",),
            default_resolution="480p",
            ratio_choices=("9:16",),
            default_ratio="9:16",
            duration_choices=(4,),
            default_duration=4,
            supports_audio=False,
            default_audio=None,
            supports_first_frame=False,
            supports_last_frame=False,
            max_reference_images=1,
            reference_image_role="reference_image",
        )
        args = build_standard_parser(roleful_spec).parse_args(
            (
                "create",
                "--prompt",
                "A reference-guided shot",
                "--reference-image",
                "https://cdn.example/reference.png",
            )
        )

        payload = build_standard_payload(roleful_spec, args)

        self.assertEqual(
            payload["content"],
            [
                {
                    "type": "image_url",
                    "image_url": "https://cdn.example/reference.png",
                    "role": "reference_image",
                }
            ],
        )

    def test_network_create_requires_confirm_paid(self) -> None:
        result = _run(
            "--base-url",
            "http://127.0.0.1:1",
            "--trust-custom-base-url",
            "--allow-insecure-localhost",
            "create",
            "--prompt",
            "A paid task must be explicit",
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("--confirm-paid", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_dry_run_emits_one_json_payload_without_confirm_paid(self) -> None:
        result = _run(
            "--json",
            "create",
            "--dry-run",
            "--prompt",
            "No network call",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["model"], "doubao-seedance-2.5")
        self.assertEqual(result.stdout.count("\n"), 1)


if __name__ == "__main__":
    unittest.main()
