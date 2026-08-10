#!/usr/bin/env python3
"""Create or run a Kling V3 Omni video generation task."""

from __future__ import annotations

import argparse

from _video_common import StandardModelSpec, UserError, run_standard_model


def validate_kling_v3_omni(args: argparse.Namespace) -> None:
    """Allow either roleful frames or roleless references, but never both."""

    if args.last_frame and not args.first_frame:
        raise UserError("--last-frame requires --first-frame for Kling V3 Omni.")
    if (args.first_frame or args.last_frame) and args.reference_image:
        raise UserError(
            "Kling V3 Omni accepts roleful frames or roleless references, not both."
        )
    if len(args.reference_image) > 2:
        raise UserError("Kling V3 Omni supports at most two roleless references.")


MODEL_SPEC = StandardModelSpec(
    canonical_id="kling-v3-omni",
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
    max_reference_images=2,
    validate=validate_kling_v3_omni,
)


def main(argv: list[str] | None = None) -> int:
    return run_standard_model(MODEL_SPEC, argv)


if __name__ == "__main__":
    raise SystemExit(main())
