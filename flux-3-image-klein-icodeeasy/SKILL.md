---
name: flux-3-image-klein-icodeeasy
description: Use when the user requests static image generation or reference-based image generation on iCodeEasy with the exact model FLUX 3 Image Klein (flux-3-image-klein), or explicitly invokes $flux-3-image-klein-icodeeasy.
---

# FLUX 3 Image Klein via iCodeEasy

固定使用 `--model flux-3-image-klein`。`--resolution` 和 `--aspect-ratio` 控制分辨率档位和比例，默认 `1k`、`1:1`。可用 `--seed` 固定随机种子。

从本 skill 目录解析共享脚本 [generate_image.py](../icodeeasy-image-generations/scripts/generate_image.py) 的绝对路径，再从用户项目目录运行。文生图和参考图生图都用 `generate`。参考图用可重复的 `--image-file` 或 `--image-url` 提交。每个任务生成一张图。

```bash
python3 /absolute/path/to/icodeeasy-image-generations/scripts/generate_image.py generate \
  --model flux-3-image-klein --resolution 1k --aspect-ratio 1:1 --seed 42 \
  --prompt "窗边的蓝釉陶杯，柔和侧光" \
  --async --wait --download-dir ./out/images --json
```

用户明确要求生图时可调用 API。仅查看参数可加 `--dry-run` 离线检查。成功后展示本地绝对路径并注明型号。已有任务 ID 时，用同一脚本的 `poll TASK_ID --wait --download-dir ./out/images --json` 恢复原任务。尺寸、比例和参考图限制见 [FLUX API 参考](../icodeeasy-image-generations/references/api.md#flux)。
