#!/usr/bin/env python3
"""Create or run a Kling 3.0 Turbo video generation task."""

from __future__ import annotations

import argparse

from _video_common import StandardModelSpec, UserError, run_standard_model


def validate_kling_v3_0_turbo(args: argparse.Namespace) -> None:
    """Require an opening frame when a closing frame is requested."""

    if getattr(args, "last_frame", None) and not args.first_frame:
        raise UserError("--last-frame requires --first-frame for Kling 3.0 Turbo.")


MODEL_SPEC = StandardModelSpec(
    canonical_id="kling-3.0-turbo",
    resolution_choices=("720p", "1080p"),
    default_resolution="720p",
    ratio_choices=("16:9", "9:16", "1:1"),
    default_ratio="9:16",
    duration_choices=tuple(range(3, 16)),
    default_duration=5,
    supports_audio=False,
    default_audio=None,
    supports_first_frame=True,
    supports_last_frame=False,
    max_reference_images=0,
    validate=validate_kling_v3_0_turbo,
)


def main(argv: list[str] | None = None) -> int:
    return run_standard_model(MODEL_SPEC, argv)


if __name__ == "__main__":
    raise SystemExit(main())
