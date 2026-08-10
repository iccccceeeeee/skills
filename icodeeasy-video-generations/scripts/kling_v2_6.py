#!/usr/bin/env python3
"""Create or run a Kling 2.6 video generation task."""

from __future__ import annotations

import argparse

from _video_common import StandardModelSpec, UserError, run_standard_model


def validate_kling_v2_6(args: argparse.Namespace) -> None:
    """Apply Kling 2.6's resolution, frame, and audio combination rules."""

    if args.generate_audio and args.resolution != "1080p":
        raise UserError("--generate-audio requires --resolution 1080p for Kling 2.6.")
    if args.last_frame:
        if not args.first_frame:
            raise UserError("--last-frame requires --first-frame for Kling 2.6.")
        if args.resolution != "1080p":
            raise UserError("--last-frame requires --resolution 1080p for Kling 2.6.")
        if args.generate_audio:
            raise UserError("--last-frame cannot be combined with --generate-audio for Kling 2.6.")


MODEL_SPEC = StandardModelSpec(
    canonical_id="kling-v2-6",
    resolution_choices=("720p", "1080p"),
    default_resolution="720p",
    ratio_choices=("16:9", "9:16", "1:1"),
    default_ratio="9:16",
    duration_choices=(5, 10),
    default_duration=5,
    supports_audio=True,
    default_audio=False,
    supports_first_frame=True,
    supports_last_frame=True,
    max_reference_images=0,
    validate=validate_kling_v2_6,
)


def main(argv: list[str] | None = None) -> int:
    return run_standard_model(MODEL_SPEC, argv)


if __name__ == "__main__":
    raise SystemExit(main())
