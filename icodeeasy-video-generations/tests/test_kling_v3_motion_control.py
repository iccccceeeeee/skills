"""Kling V3 Motion Control command contract."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _video_common import build_motion_parser, build_motion_payload  # noqa: E402
from kling_v3_motion_control import MODEL_SPEC  # noqa: E402


class KlingV3MotionControlTests(unittest.TestCase):
    def test_v3_owns_its_canonical_model_id(self) -> None:
        args = build_motion_parser(MODEL_SPEC).parse_args(
            (
                "create",
                "--reference-image",
                "https://cdn.example/reference.png",
                "--reference-video",
                "https://cdn.example/motion.mp4",
            )
        )

        payload = build_motion_payload(MODEL_SPEC, args)
        self.assertEqual(payload["model"], "kling-v3-motion-control")
        self.assertNotEqual(payload["model"], "kling-v2-6-motion-control")

    def test_create_and_run_share_motion_only_options(self) -> None:
        parser = build_motion_parser(MODEL_SPEC)
        run_args = parser.parse_args(
            (
                "run",
                "--mode",
                "pro",
                "--orientation",
                "video",
                "--reference-image",
                "https://cdn.example/reference.png",
                "--reference-video",
                "https://cdn.example/motion.mp4",
                "--output",
                "result.mp4",
            )
        )

        self.assertEqual(build_motion_payload(MODEL_SPEC, run_args)["mode"], "pro")
        self.assertEqual(run_args.output, "result.mp4")


if __name__ == "__main__":
    unittest.main()
