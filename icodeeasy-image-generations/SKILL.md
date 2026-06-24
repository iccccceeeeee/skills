---
name: icodeeasy-image-generations
description: Use when generating or editing pictures through the iCodeEasy OpenAI-compatible Images API with gpt-image-2, including /v1/images/generations, /v1/images/edits, reference images through image_urls, async image tasks, and credentials from OPENAI_API_KEY or ANTHROPIC_AUTH_TOKEN.
---

# iCodeEasy Image Generations

## 核心范围

通过 iCodeEasy 的 OpenAI 兼容 Images API 调用 `gpt-image-2`：

- 文生图默认用 `https://jp.icodeeasy.cc/v1/images/generations`。
- 明确编辑已有图片时用 `https://jp.icodeeasy.cc/v1/images/edits`，并把参考图放进 JSON 的 `image_urls` 字段。
- 不要传 `size`。让接口使用默认尺寸策略，脚本也不暴露 `--size`。

默认认证从环境变量读取：

- 优先 `OPENAI_API_KEY`
- 没有时回退到 `ANTHROPIC_AUTH_TOKEN`

不要打印、保存或回显 API key。图片结果 URL 本身就是凭据，只把完整链接发给请求者，不要贴到公开渠道。

## 推荐入口

优先用脚本，不要手写 curl：

```bash
python3 scripts/generate_image.py generate --prompt "一只橘猫坐在窗台上看夕阳，水彩画风格"
```

常用参数：

- `--resolution`: 默认 `1k`，可选 `1k` 或 `2k`。
- `--quality`: 默认 `medium`，可选 `low`、`medium`、`high`、`auto`。这个字段只决定计费档，不改变实际输出质量语义。
- `--n`: 生成张数，按张计费。
- `--image-url`: 参考图 URL 或 data URL，可重复，URL 必须是 `https://`。
- `--image-file`: 本地参考图，可重复，脚本会转成 `data:image/*;base64,...` 放进 `image_urls`。
- `--download-dir`: 下载返回的图片到本地目录。
- `--json`: 输出机器可读结果。

## 工作流

1. 抽取用户的 prompt、张数、分辨率、质量档和参考图。
2. 如果用户没有明确授权调用这个付费外部 API，先确认一次。
3. 文生图用 `generate`。编辑图片用 `edit`，并且必须提供至少一张 `--image-file` 或 `--image-url`。
4. 请求可能等待 30 到 60 秒以上；不想阻塞时用 `--async`，再用 `poll` 子命令取结果。
5. 返回结果时给图片 URL 或本地下载路径，并说明使用的模型、质量档和张数。

## 示例

同步生成并下载：

```bash
python3 scripts/generate_image.py generate \
  --prompt "a corgi astronaut on the moon, cinematic" \
  --resolution 2k \
  --quality medium \
  --download-dir ./out/images
```

编辑已有图片：

```bash
python3 scripts/generate_image.py edit \
  --prompt "把这个人物改成 70 岁，保留原构图和光线" \
  --image-file /path/to/photo.png
```

异步提交并轮询：

```bash
python3 scripts/generate_image.py generate --async --prompt "赛博朋克城市雨夜，电影感" --json
python3 scripts/generate_image.py poll d142c93a-de26-40c9-be62-0de840d10960 --wait --json
```

调用前检查 payload，不联网：

```bash
python3 scripts/generate_image.py generate \
  --prompt "minimal product photo of a ceramic cup" \
  --dry-run \
  --json
```

## 错误处理

- `400`: 检查参考图数量、URL 是否为 `https://`、base64 是否是合法 data URL。
- `401`: 检查 `OPENAI_API_KEY` 或 `ANTHROPIC_AUTH_TOKEN`。
- `402`: 余额或额度不足。
- `429`: 降低并发或稍后重试。
- `5xx`: 服务暂时不可用或生成失败，可以稍后重试。

失败请求按接口文档不计费。不要把失败归因写死，除非响应体明确说明原因。

## 参考

需要查参数边界时读 `references/api.md`。脚本参数以 `python3 scripts/generate_image.py --help` 和子命令 `--help` 为准。
