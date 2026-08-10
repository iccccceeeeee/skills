---
name: icodeeasy-video-generations
description: Use when creating, polling, downloading, or deleting iCodeEasy asynchronous video-generation tasks with the supported Seedance, MiniMax, Grok, or Kling video models.
---

# iCodeEasy Video Generations

Create asynchronous video tasks through the iCodeEasy Video API. Use the model-specific Python command so its validation matches the selected model.

## Safe workflow

1. Choose the model and its exact script from [the API reference](references/api.md). Read the script's `--help` for its supported flags and combinations.
2. This API can create paid tasks. Confirm the user explicitly authorizes the paid API call, then pass `--confirm-paid`. Use `--dry-run` to inspect a request without a network call.
3. Prefer `run` when creating a task: it creates once, polls that same task, and can download with `--output`. Use `create` only when the caller will retain the task ID and poll later.
4. For an existing task, use `python3 scripts/video_task.py poll|download|delete`; do not create a duplicate task.

Credentials are read from `OPENAI_API_KEY`, then `ANTHROPIC_AUTH_TOKEN`. Do not print, save, or commit keys. Public HTTPS reference URLs are accepted where that model's help says they are supported.

## Example

```bash
python3 scripts/doubao_seedance_2_5.py run \
  --confirm-paid \
  --prompt "A lantern boat crossing a misty lake at dawn" \
  --output ./out/lake.mp4
```

If submission status is uncertain, retain the task ID and idempotency key, then retry only with the same `--idempotency-key`. Read [references/api.md](references/api.md) for task lifecycle, idempotency, and error handling.
