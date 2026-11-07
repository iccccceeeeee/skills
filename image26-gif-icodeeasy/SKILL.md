---
name: image26-gif-icodeeasy
description: Use when the user asks to generate animated GIFs, looping animations, or $image26-gif-icodeeasy with Image 2.6 through iCodeEasy. Generates GIFs from text with optional reference images, waits for completion, and delivers local animation files.
---

# Image 2.6 GIF

用户可以直接说“用 Image 2.6 生成一只猫挥手的 GIF”，或调用 `$image26-gif-icodeeasy` 并描述动画。根据当前对话提取需求，生成并展示动图。

## 默认行为

- 默认使用 `gpt-image-2.6-flare`。用户明确指定 Sunburst 时使用 `gpt-image-2.6-sunburst`。
- 每个任务生成一段 GIF。纯文生 GIF 标准价为每个成功结果 ¥0.0833，参考图生成 GIF 按实际用量结算。
- 帧数、帧间隔和尺寸由模型决定。用户要求固定时长或尺寸时，说明输出参数为自动设置。
- 用户要多段动画时，逐段提交独立任务。
- 用户要把已有图片做成动图时，用 `generate` 加上 `--image-file` 或 `--image-url`。两种参数均可重复，总计最多八张。
- 默认等待完成，将 GIF 下载到用户项目的 `out/images/`，以本地绝对路径展示动画，保留原始 GIF 字节。

静态图片生成和编辑入口为独立的 `$image26-icodeeasy`。

用户明确要求用本 skill 生成 GIF，即可执行付费调用。如果只是在询问功能、价格或写提示词，先回答该问题。

## 执行

脚本位于本 skill 的 `scripts/generate_image.py`。执行时把脚本路径解析为绝对路径，当前目录保留为用户的项目目录。

```bash
python3 scripts/generate_image.py generate \
  --prompt "一盏纸灯笼在夜风中轻轻摇晃，无缝循环" \
  --async --wait --download-dir ./out/images --json
```

脚本默认生成 GIF。认证优先读取 `OPENAI_API_KEY`，没有时读取 `ANTHROPIC_AUTH_TOKEN`。缺少认证时说明需要配置密钥。密钥只通过环境变量使用。

## 结果与恢复

- 成功后展示本地 `.gif` 文件的绝对路径，并简短说明使用了 Image 2.6 GIF。
- 保存任务 ID。轮询超时、网络中断或下载失败时，继续查询和下载同一个任务。
- 用 `poll <task_id> --wait --download-dir ./out/images --json` 恢复结果。已创建的任务不应因等待或下载失败而重复提交。
- 结果链接长期有效，按持有链接即可访问的敏感信息处理。仅在用户需要时提供完整链接。

参数边界、模型变体和恢复命令见 [API 参考](references/api.md)。
