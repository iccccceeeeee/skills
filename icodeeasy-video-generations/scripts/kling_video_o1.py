#!/usr/bin/env python3
"""Create or run a Kling Video O1 generation task."""

from __future__ import annotations

import argparse

from _video_common import StandardModelSpec, UserError, run_standard_model


def validate_kling_video_o1(args: argparse.Namespace) -> None:
    """Keep Kling Video O1 closing frames paired with an opening frame."""

    if args.last_frame and not args.first_frame:
        raise UserError("--last-frame requires --first-frame for Kling Video O1.")


MODEL_SPEC = StandardModelSpec(
    canonical_id="kling-video-o1",
    resolution_choices=("720p", "1080p"),
    default_resolution="720p",
    ratio_choices=("16:9", "9:16", "1:1"),
    default_ratio="9:16",
    duration_choices=(5, 10),
    default_duration=5,
    supports_audio=False,
    default_audio=None,
    supports_first_frame=True,
    supports_last_frame=True,
    max_reference_images=0,
    validate=validate_kling_video_o1,
)


def main(argv: list[str] | None = None) -> int:
    return run_standard_model(MODEL_SPEC, argv)


if __name__ == "__main__":
    raise SystemExit(main())
