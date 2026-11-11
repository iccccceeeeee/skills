---
name: seedream-4-5-icodeeasy
description: Use when generating or transforming static images on iCodeEasy with Seedream 4.5 (`seedream-4-5`) or $seedream-4-5-icodeeasy.
---

# Seedream 4.5 via iCodeEasy

固定使用 `--model seedream-4-5`。默认 2K、`1:1`、每个任务一张图。分辨率可选 2K、4K，最多 8 张参考图。比例和认证方式见 [Seedream API 参考](../icodeeasy-image-generations/references/api.md#seedream)。

文生图和参考图生图都用 `generate`。有参考图时追加 `--image-file` 或 `--image-url`，可重复。将 [共享脚本](../icodeeasy-image-generations/scripts/generate_image.py) 路径解析为绝对路径，从用户项目目录运行。

```bash
python3 /absolute/path/to/icodeeasy-image-generations/scripts/generate_image.py generate \
  --model seedream-4-5 --resolution 2k --aspect-ratio 16:9 \
  --prompt "午后窗边的陶杯，暖色静物摄影" \
  --async --wait --download-dir ./out/images --json
```

用户明确要求生成时可调用付费 API。只需检查请求时追加 `--dry-run`。生成后展示本地绝对路径并注明模型。已有任务 ID 时用 `poll TASK_ID --wait --download-dir ./out/images --json` 恢复同一任务。
