#!/usr/bin/env python3
"""Poll, download, or delete an existing iCodeEasy video task."""

from __future__ import annotations

import argparse

from _video_common import (
    ProtocolError,
    UserError,
    delete_task,
    download_task,
    emit_result,
    emit_operation_error,
    normalize_base_url,
    poll_task,
    positive_float,
    resolve_api_key,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="https://api.icodeeasy.cc")
    parser.add_argument("--trust-custom-base-url", action="store_true")
    parser.add_argument("--allow-insecure-localhost", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--timeout", type=positive_float, default=60)
    commands = parser.add_subparsers(dest="command", required=True)

    poll = commands.add_parser("poll", help="fetch a task or wait for completion")
    poll.add_argument("task_id")
    poll.add_argument("--wait", action="store_true")
    poll.add_argument("--interval", type=positive_float, default=5)
    poll.add_argument("--max-wait", type=positive_float, default=900)

    download = commands.add_parser("download", help="download completed video content")
    download.add_argument("task_id")
    download.add_argument("--output", required=True)
    download.add_argument("--overwrite", action="store_true")

    delete = commands.add_parser("delete", help="delete a task when the API permits it")
    delete.add_argument("task_id")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        base_url = normalize_base_url(
            args.base_url,
            trust_custom=args.trust_custom_base_url,
            allow_insecure_localhost=args.allow_insecure_localhost,
        )
        api_key, _source = resolve_api_key()

        if args.command == "poll":
            task = poll_task(
                base_url,
                args.task_id,
                api_key,
                wait=args.wait,
                interval=args.interval,
                max_wait=args.max_wait,
                timeout=args.timeout,
            )
            status = task.get("status")
            if status == "failed" or status not in {"queued", "running", "succeeded"}:
                emit_result(task, json_mode=args.json)
                return 1
            emit_result(task, json_mode=args.json)
            return 0

        if args.command == "download":
            output = download_task(
                base_url,
                args.task_id,
                args.output,
                api_key,
                overwrite=args.overwrite,
                timeout=args.timeout,
            )
            emit_result(
                {"ok": True, "output": str(output), "summary": f"Downloaded to {output}"},
                json_mode=args.json,
            )
            return 0

        result = delete_task(base_url, args.task_id, api_key, timeout=args.timeout)
        emit_result(
            {
                "ok": True,
                "task_id": args.task_id,
                "response": result,
                "summary": "Task deleted.",
            },
            json_mode=args.json,
        )
        return 0
    except (UserError, ProtocolError) as exc:
        emit_operation_error(
            exc, json_mode=args.json, accepted_task_id=args.task_id, stage=args.command,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
