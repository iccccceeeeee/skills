#!/usr/bin/env python3
"""Create or run a MiniMax H3 video generation task."""

from __future__ import annotations

from _video_common import StandardModelSpec, run_standard_model


MODEL_SPEC = StandardModelSpec(
    canonical_id="MiniMax-H3",
    resolution_choices=("768P", "2K"),
    default_resolution="768P",
    ratio_choices=("21:9", "16:9", "4:3", "1:1", "3:4", "9:16"),
    default_ratio="9:16",
    duration_choices=tuple(range(4, 16)),
    default_duration=5,
    supports_audio=False,
    default_audio=None,
    supports_first_frame=True,
    supports_last_frame=True,
    max_reference_images=0,
)


def main(argv: list[str] | None = None) -> int:
    return run_standard_model(MODEL_SPEC, argv)


if __name__ == "__main__":
    raise SystemExit(main())
