---
name: image25-sunburst-icodeeasy
description: Use when generating or editing static images with Image 2.5 Sunburst (gpt-image-2.5-sunburst, also written sunbrust) on iCodeEasy or invoking $image25-sunburst-icodeeasy.
---

# Image 2.5 Sunburst

此入口固定使用 `gpt-image-2.5-sunburst`。提交生成或编辑请求时显式传入下列 `--model`。

文生图用 `generate`。编辑用 `edit` 并添加 `--image-file` 或 `--image-url`。默认 1K，分辨率用 `--resolution`，比例用 `--aspect-ratio`。 详见 [API 参考](../image25-icodeeasy/references/api.md)。

使用 [生成脚本](../image25-icodeeasy/scripts/generate_image.py)，将示例中的脚本路径替换为实际绝对路径，在用户的项目目录执行。

```bash
python3 /absolute/path/to/image25-icodeeasy/scripts/generate_image.py generate \
  --model gpt-image-2.5-sunburst --prompt "窗边的一只蓝釉陶杯，柔和的晨光" \
  --async --wait --download-dir ./out/images --json
```

用户明确要求生成或编辑图片时提交请求。可加 `--dry-run` 离线预检。完成后展示本地图片的绝对路径，注明实际型号。等待或下载中断时用同一脚本的 `poll TASK_ID --wait --download-dir ./out/images --json` 恢复任务。
