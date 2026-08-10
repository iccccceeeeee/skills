#!/usr/bin/env python3
"""Create or run a Seedance 1.5 Pro video generation task."""

from __future__ import annotations

from _video_common import StandardModelSpec, run_standard_model


MODEL_SPEC = StandardModelSpec(
    canonical_id="doubao-seedance-1.5-pro",
    resolution_choices=("480p", "720p", "1080p"),
    default_resolution="480p",
    ratio_choices=("16:9", "4:3", "1:1", "3:4", "9:16", "21:9"),
    default_ratio="9:16",
    duration_choices=tuple(range(4, 13)),
    default_duration=4,
    supports_audio=True,
    default_audio=True,
    supports_first_frame=False,
    supports_last_frame=False,
    max_reference_images=0,
)


def main(argv: list[str] | None = None) -> int:
    return run_standard_model(MODEL_SPEC, argv)


if __name__ == "__main__":
    raise SystemExit(main())
