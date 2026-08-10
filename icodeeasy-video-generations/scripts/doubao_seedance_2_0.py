#!/usr/bin/env python3
"""Create or run a Seedance 2.0 video generation task."""

from __future__ import annotations

from _video_common import StandardModelSpec, require_first_frame_for_last_frame, run_standard_model


MODEL_SPEC = StandardModelSpec(
    canonical_id="doubao-seedance-2.0",
    resolution_choices=("480p", "720p", "1080p", "4K"),
    default_resolution="480p",
    ratio_choices=("16:9", "4:3", "1:1", "3:4", "9:16", "21:9", "adaptive"),
    default_ratio="9:16",
    duration_choices=tuple(range(4, 16)),
    default_duration=4,
    supports_audio=True,
    default_audio=True,
    supports_first_frame=True,
    supports_last_frame=True,
    max_reference_images=0,
    validate=require_first_frame_for_last_frame,
)


def main(argv: list[str] | None = None) -> int:
    return run_standard_model(MODEL_SPEC, argv)


if __name__ == "__main__":
    raise SystemExit(main())
