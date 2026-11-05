---
name: image2-icodeeasy
description: Use when the user asks to generate or edit images with Image 2, GPT Image 2, or $image2-icodeeasy through iCodeEasy. Handles text prompts, reference images, waiting for results, and local image delivery.
---

# Image 2

用户可以直接说“用 Image 2 画一只猫”，或调用 `$image2-icodeeasy` 并描述画面。根据当前对话提取需求，执行生成或编辑，再展示图片。

## 默认行为

- 默认模型为 `gpt-image-2`。
- 默认生成一张图片，使用 `1k` 分辨率和 `medium` 画质设置。
- 用户没有指定参数时直接使用默认值。用户指定尺寸、比例或张数时，按 [API 参考](references/api.md) 选择参数。
- 用户要多张图片时，逐张提交独立任务，每个任务设置 `n=1`。
- 用户要求修改已有图片时，使用 `edit` 并附上参考图。参考图可以来自当前对话、本地文件或 HTTPS 链接。
- 默认等待任务完成，将图片下载到用户项目的 `out/images/`，然后以绝对路径展示图片。

用户明确要求用本 skill 生成或编辑图片，即可执行付费调用。如果只是在询问功能、价格或写提示词，先回答该问题。

## 执行

脚本位于本 skill 的 `scripts/generate_image.py`。执行时把脚本路径解析为绝对路径，当前目录保留为用户的项目目录。

生成并等待结果的基本命令如下。

```bash
python3 scripts/generate_image.py generate \
  --prompt "一只橘猫坐在窗台上看夕阳，水彩画风格" \
  --async --wait --download-dir ./out/images --json
```

编辑图片时使用以下形式。

```bash
python3 scripts/generate_image.py edit \
  --prompt "把背景改成海边日落，保留人物和服装" \
  --image-file /path/to/photo.png \
  --async --wait --download-dir ./out/images --json
```

认证优先读取 `OPENAI_API_KEY`，没有时读取 `ANTHROPIC_AUTH_TOKEN`。缺少认证时说明需要配置密钥。密钥只通过环境变量使用。

## 结果与恢复

- 成功后展示下载图片的绝对路径，并简短说明使用了 Image 2。
- 保存本次任务 ID。轮询超时、网络中断或下载失败时，继续查询和下载同一个任务。
- 用 `poll <task_id> --wait --download-dir ./out/images --json` 恢复结果。已创建的任务不应因等待或下载失败而重复提交。
- 图片链接长期有效，按持有链接即可访问的敏感信息处理。仅在用户需要时提供完整链接。

参数、模型变体和恢复命令见 [API 参考](references/api.md)。
