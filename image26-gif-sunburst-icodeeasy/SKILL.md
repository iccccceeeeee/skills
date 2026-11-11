---
name: image26-gif-sunburst-icodeeasy
description: Use when generating animated GIFs with Image 2.6 Sunburst (gpt-image-2.6-sunburst) on iCodeEasy or invoking $image26-gif-sunburst-icodeeasy. Also use for unversioned Sunburst (sunbrust) GIF requests.
---

# Image 2.6 Sunburst GIF

此入口固定使用 `gpt-image-2.6-sunburst`。提交请求时显式传入下列 `--model`。

使用 `generate` 创建 GIF，可用 `--image-file` 或 `--image-url` 添加参考图。帧数、帧间隔和尺寸自动设置。详见 [API 参考](../image26-gif-icodeeasy/references/api.md)。

使用 [生成脚本](../image26-gif-icodeeasy/scripts/generate_image.py)，将示例中的脚本路径替换为实际绝对路径，在用户的项目目录执行。

```bash
python3 /absolute/path/to/image26-gif-icodeeasy/scripts/generate_image.py generate \
  --model gpt-image-2.6-sunburst --prompt "纸灯笼在夜风中轻轻摇晃，无缝循环" \
  --async --wait --download-dir ./out/images --json
```

用户明确要求生成 GIF 时提交请求。可加 `--dry-run` 离线预检。完成后展示本地 GIF 绝对路径，注明实际型号。等待或下载中断时用同一脚本的 `poll TASK_ID --wait --download-dir ./out/images --json` 恢复任务。
