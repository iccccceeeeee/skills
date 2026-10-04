# iCodeEasy Video API Reference

## Authentication and safety

Commands use `OPENAI_API_KEY`, falling back to `ANTHROPIC_AUTH_TOKEN`. A network `create` or `run` requires `--confirm-paid`; use `--dry-run` first if authorization is absent or the payload needs review. Never print, commit, or otherwise expose credentials.

The default API base is `https://api.icodeeasy.cc`. `--base-url` accepts the official backup domains; a custom base requires `--trust-custom-base-url`. The scripts accept public HTTPS reference media only.

## Select a model command

Run the selected script with `--help` for its exact model-specific flags, limits, defaults, and incompatible combinations.

| Public model | Command |
| --- | --- |
| Seedance 2.5 | `python3 scripts/doubao_seedance_2_5.py` |
| Seedance 2.0 | `python3 scripts/doubao_seedance_2_0.py` |
| Seedance 2.0 Fast | `python3 scripts/doubao_seedance_2_0_fast.py` |
| Seedance 2.0 Mini | `python3 scripts/doubao_seedance_2_0_mini.py` |
| Seedance 1.5 Pro | `python3 scripts/doubao_seedance_1_5_pro.py` |
| MiniMax H3 | `python3 scripts/minimax_h3.py` |
| Grok Imagine 1.5 Video | `python3 scripts/grok_imagine_1_5_video.py` |
| Kling 2.6 | `python3 scripts/kling_v2_6.py` |
| Kling 3.0 Turbo | `python3 scripts/kling_v3_0_turbo.py` |
| Kling V3 | `python3 scripts/kling_v3.py` |
| Kling V3 Omni | `python3 scripts/kling_v3_omni.py` |
| Kling Video O1 | `python3 scripts/kling_video_o1.py` |
| Kling 2.6 Motion Control | `python3 scripts/kling_v2_6_motion_control.py` |
| Kling V3 Motion Control | `python3 scripts/kling_v3_motion_control.py` |

All model commands offer `create` and `run`:

- `create` submits one paid task and returns its ID.
- `run` submits once, polls that same ID until terminal state, and supports `--output` to download the completed video.

For a task that already exists, use the model-independent lifecycle tool:

```bash
mkdir -p ./out
python3 scripts/video_task.py poll TASK_ID --wait
python3 scripts/video_task.py download TASK_ID --output ./out/video.mp4
python3 scripts/video_task.py delete TASK_ID
```

Creation uses `POST /v1/videos/generations`. Existing tasks use `GET /v1/videos/tasks/{id}`, `GET /v1/videos/tasks/{id}/content`, and `DELETE /v1/videos/tasks/{id}`. The API's `status_url` and `content_url` identify those canonical paths. Keep the API base and the opaque task ID; do not derive polling URLs from the creation path.

Content retrieval may redirect twice: from the authenticated content endpoint to a signed relay file URL, then to stored media. The downloader follows up to two redirects, keeps authentication only within the API origin, and removes it permanently after a cross-origin redirect. HTTPS-to-HTTP redirects remain refused.

## Idempotency and retries

Every create request sends an `Idempotency-Key`. To recover from an uncertain submission, reuse the original key with `--idempotency-key KEY`; do not start a second task with a fresh key. The commands do not automatically retry POST requests, because an ambiguous create could otherwise duplicate a paid task. Polling and downloading an existing task are safe alternatives while resolving uncertainty.

## Results and failures

Use `--json` for machine-readable output. A task remains `queued` or `running` until it reaches `succeeded` or `failed`. `run` and `video_task.py poll --wait` accept `--interval` and `--max-wait`; use each command's `--help` for the full option set.

Check the API response before attributing a failure. In particular, `401` usually means credentials are missing or invalid, `402` indicates unavailable balance or quota, `429` indicates rate limiting, and `5xx` indicates a service-side failure. Failed requests are not assumed to be free unless the API response says so.

An unsuccessful CLI operation is distinct from an unsuccessful generation. JSON errors include `error.stage` (`submission`, `poll`, `download`, or `delete`) and HTTP status/error code when available. After an accepted create, they retain `task_id`, `idempotency_key`, the last confirmed task `status`, and a `recovery_action`:

- `poll`: the latest status could not be confirmed. A 404 or timeout does not prove generation failed. Re-query the same task ID; do not start another paid task.
- `download`: file retrieval failed. If `status` is `succeeded`, explicitly tell the user generation succeeded and retry only `video_task.py download TASK_ID --output ./out/video.mp4`.
- `reuse_idempotency_key`: submission is uncertain and no task ID was received. Retain the original key and request payload for recovery; do not submit with a fresh key.

The CLI still exits nonzero when the requested operation does not finish. Treat only a task's explicit `status: failed` as a confirmed generation failure. If file retrieval continues to fail, the API Key owner's [usage details](https://icodeeasy.cc/dashboard/logs/) provide a preview/download recovery entry for successful videos.
