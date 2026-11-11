# iCodeEasy Images API 参考

依据：[iCodeEasy 图片生成 API](https://icodeeasy.cc/docs/zh/image-generation.md)。脚本默认使用 `https://jp.icodeeasy.cc`；也可通过 `--base-url` 选 `https://api.icodeeasy.cc` 或 `https://sg.icodeeasy.cc`。认证依次读取 `OPENAI_API_KEY`、`ANTHROPIC_AUTH_TOKEN`。

- `generate` → `POST /v1/images/generations`。
- `edit` → `POST /v1/images/edits`，用于 GPT Image 参考图编辑。
- `--async --wait` 提交异步任务并等待结果。仅传 `--async` 时保存 `task_id`；随后用 `poll TASK_ID --wait`，通过 `GET /v1/images/tasks/{task_id}` 查询。同步请求也会识别意外返回的异步任务。
- `--image-file` 转成 data URL；`--image-url` 接受公网 HTTPS URL 或图片 data URL。两个参数都可重复。`--dry-run --json` 检查请求，不提交，并省略内联图片内容。

## GPT Image

- 静态图模型 ID：`gpt-image-2`、`gpt-image-2.5-flare`、`gpt-image-2.5-sunburst`、`gpt-image-2.6-flare`、`gpt-image-2.6-sunburst`。
- Flare 适合快速迭代；Sunburst 适合细节与精确编辑。2.6 的 Sunburst 在中、高质量档的细节和多轮一致性更好，这是 [OpenAI 的模型定位](https://openai.com/index/introducing-images-2-6/)。明确指定变体时用完整模型 ID。
- `--resolution` 支持 `1k` / `2k` / `4k`，默认 `1k`。`--quality` 支持 `low` / `medium` / `high` / `auto`，默认 Image 2 为 `medium`，2.5/2.6 为 `auto`。比例用 `--aspect-ratio`。
- 参考图使用 `image_urls`。Image 2.6 最多八张，2K / 4K 的参考图使用 PNG、JPEG 或 WebP。Image 2 / 2.5 的公开目录保守上限为四张。

## Seedream

文生图和参考图生图都用 `generate`。脚本发送 `image_size`、`aspect_ratio`；参考图使用 `image_input`。

| `--model` | `--resolution`（粗体为默认） | 参考图上限 |
| --- | --- | --- |
| `seedream-5-5` | `1k`, `1.5k`, **`2k`** | 10 |
| `seedream-5-0-flash` / `seedream-5-0-pro` | **`1k`**, `1.5k`, `2k` | 8 |
| `seedream-4-5` | **`2k`**, `4k` | 8 |
| `seedream-4-0` | `1k`, **`2k`**, `4k` | 8；提示词最多 1000 字符 |
| `doubao-seedream-5-0-lite` | **`2k`**, `3k` | 脚本最多接受 8 张，以实际任务为准 |

默认比例 `1:1`。5.5、5 Flash / Pro 支持 `1:1`, `4:3`, `3:4`, `16:9`, `9:16`, `3:2`, `2:3`, `2:1`, `1:2`, `21:9`；4.5 / 4.0 另支持 `9:21`。Lite 支持其中的 `1:1`, `4:3`, `3:4`, `16:9`, `9:16`, `3:2`, `2:3`, `21:9`。

## FLUX

文生图和参考图生图都用 `generate`。参考图使用 `image_input`，最多八张。

| 系列 | `--model` | 尺寸参数 |
| --- | --- | --- |
| FLUX 2 | `flux-2-pro`, `flux-2-max`, `flux-2-flex` | `--size WIDTHxHEIGHT`，默认 `1024x1024`。每边至少 64，输出最多 4 MP；输出与参考图合计最多 9 MP。 |
| FLUX 3 | `flux-3-image`, `flux-3-image-klein` | `--resolution 768sq/1k/1.5k/2k/4k`，默认 `1k`；`--aspect-ratio` 默认 `1:1`。 |

FLUX 3 支持 `1:1`, `9:16`, `16:9`, `2:3`, `3:2`, `4:5`, `5:4`，使用档位和比例而非像素尺寸。`--seed` 支持 FLUX 2 和 FLUX 3 Image Klein，范围 `0` 至 `4294967295`。

## 恢复和结果

图片链接来自同步响应的 `data[].url` 或任务的 `result_url`。`--download-dir` 保存文件；结果链接无需密钥即可访问，不应公开分享。实际价格以成功任务的账单为准。
