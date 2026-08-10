#!/usr/bin/env python3
"""Create or run a Kling V3 video generation task."""

from __future__ import annotations

import argparse

from _video_common import StandardModelSpec, UserError, run_standard_model


def validate_kling_v3(args: argparse.Namespace) -> None:
    """Keep Kling V3 closing frames paired with an opening frame."""

    if args.last_frame and not args.first_frame:
        raise UserError("--last-frame requires --first-frame for Kling V3.")


MODEL_SPEC = StandardModelSpec(
    canonical_id="kling-v3",
    resolution_choices=("720p", "1080p", "4K"),
    default_resolution="720p",
    ratio_choices=("16:9", "9:16", "1:1"),
    default_ratio="9:16",
    duration_choices=tuple(range(3, 16)),
    default_duration=5,
    supports_audio=True,
    default_audio=True,
    supports_first_frame=True,
    supports_last_frame=True,
    max_reference_images=0,
    validate=validate_kling_v3,
)


def main(argv: list[str] | None = None) -> int:
    return run_standard_model(MODEL_SPEC, argv)


if __name__ == "__main__":
    raise SystemExit(main())
