---
name: icodeeasy-image-generations
description: Use when explicitly invoking $icodeeasy-image-generations, using the iCodeEasy Images API, or choosing among GPT Image, Seedream, and FLUX image models on iCodeEasy.
---

# iCodeEasy Image Generations

使用本 skill 的 `scripts/generate_image.py` 生成或编辑静态图片、查询任务及下载结果。把脚本路径解析为绝对路径，从用户项目目录执行。

| 用户选择 | `--model` | 有参考图时的命令 |
| --- | --- | --- |
| Image 2，或未指定模型 | `gpt-image-2` | `edit` |
| Image 2.5 Flare / Sunburst | `gpt-image-2.5-flare` / `gpt-image-2.5-sunburst` | `edit` |
| Image 2.6 Flare / Sunburst | `gpt-image-2.6-flare` / `gpt-image-2.6-sunburst` | `edit` |
| Seedream | 默认 `seedream-5-5`；见 [Seedream 型号](references/api.md#seedream) | `generate` |
| FLUX | 默认 `flux-3-image`，FLUX 2 默认 `flux-2-pro`；见 [FLUX 型号](references/api.md#flux) | `generate` |

只说 Flare 或 Sunburst（也接受 `sunbrust` 的写法）时用 Image 2.6。指定 2.5 或 2.6 而未指定变体时用对应版本的 Flare。保留用户明确指定的版本、变体和输出格式。

| 输出 | Flare | Sunburst |
| --- | --- | --- |
| Image 2.5 静态图 | [$image25-flare-icodeeasy](../image25-flare-icodeeasy/SKILL.md) | [$image25-sunburst-icodeeasy](../image25-sunburst-icodeeasy/SKILL.md) |
| Image 2.6 静态图 | [$image26-flare-icodeeasy](../image26-flare-icodeeasy/SKILL.md) | [$image26-sunburst-icodeeasy](../image26-sunburst-icodeeasy/SKILL.md) |
| Image 2.6 GIF | [$image26-gif-flare-icodeeasy](../image26-gif-flare-icodeeasy/SKILL.md) | [$image26-gif-sunburst-icodeeasy](../image26-gif-sunburst-icodeeasy/SKILL.md) |

各子型号的独立入口见 [Seedream 系列](../seedream-icodeeasy/SKILL.md)和 [FLUX 系列](../flux-icodeeasy/SKILL.md)。

文生图用 `generate`。用 `--image-file` 或 `--image-url` 添加参考图，可重复。每个任务生成一张；需要多张时逐张提交。尺寸、比例、参考图上限按[对应模型的 API 参考](references/api.md)选择。

```bash
python3 scripts/generate_image.py generate --model gpt-image-2.6-sunburst \
  --prompt "夕阳下的木质栈桥，水彩" --async --wait --download-dir ./out/images --json
```

用户明确要求通过本 skill 生成或编辑时，可调用付费 API。只询问模型、参数或价格时不发生成请求。认证依次读取 `OPENAI_API_KEY`、`ANTHROPIC_AUTH_TOKEN`，不要输出密钥。`--dry-run --json` 可在无密钥、无网络的情况下核对请求。

默认保存到项目的 `out/images/`，展示本地绝对路径，并说明实际使用的模型。结果链接按持有即可访问的敏感信息处理。提交成功后若轮询超时或下载失败，用 `poll TASK_ID --wait --download-dir ./out/images --json` 恢复原任务。
