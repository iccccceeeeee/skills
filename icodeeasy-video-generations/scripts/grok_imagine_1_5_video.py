#!/usr/bin/env python3
"""Create or run a Grok Imagine 1.5 Video generation task."""

from __future__ import annotations

from _video_common import StandardModelSpec, run_standard_model


MODEL_SPEC = StandardModelSpec(
    canonical_id="grok-imagine-1.5-video",
    resolution_choices=("480p", "720p"),
    default_resolution="480p",
    ratio_choices=("16:9", "9:16", "1:1", "3:2", "2:3"),
    default_ratio="9:16",
    duration_choices=tuple(range(6, 31)),
    default_duration=6,
    supports_audio=False,
    default_audio=None,
    supports_first_frame=False,
    supports_last_frame=False,
    max_reference_images=7,
)


def main(argv: list[str] | None = None) -> int:
    return run_standard_model(MODEL_SPEC, argv)


if __name__ == "__main__":
    raise SystemExit(main())
