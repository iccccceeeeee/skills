#!/usr/bin/env python3
"""Create or run a Kling V3 Motion Control video task."""

from __future__ import annotations

from _video_common import MotionModelSpec, run_motion_model


MODEL_SPEC = MotionModelSpec(canonical_id="kling-v3-motion-control")


def main(argv: list[str] | None = None) -> int:
    return run_motion_model(MODEL_SPEC, argv)


if __name__ == "__main__":
    raise SystemExit(main())
