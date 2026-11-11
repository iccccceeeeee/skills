# Ice Skills

Codex skills for local workflows.

English version: [README.en.md](README.en.md)

Skills 安装到 `~/.codex/skills/`。下面的安装命令使用 `curl` 和 `tar`。

## Skills

### 图片生成

按模型和输出格式选择 skill，直接描述想要的画面。

| 模型与输出 | Skill |
| --- | --- |
| Image 2 | [image2-icodeeasy](image2-icodeeasy/SKILL.md) |
| Image 2.5 静态图片 | [Flare](image25-flare-icodeeasy/SKILL.md) · [Sunburst](image25-sunburst-icodeeasy/SKILL.md) |
| Image 2.6 静态图片 | [Flare](image26-flare-icodeeasy/SKILL.md) · [Sunburst](image26-sunburst-icodeeasy/SKILL.md) |
| Image 2.6 GIF | [Flare](image26-gif-flare-icodeeasy/SKILL.md) · [Sunburst](image26-gif-sunburst-icodeeasy/SKILL.md) |
| Seedream 5 | [5.5](seedream-5-5-icodeeasy/SKILL.md) · [5 Flash](seedream-5-0-flash-icodeeasy/SKILL.md) · [5 Pro](seedream-5-0-pro-icodeeasy/SKILL.md) · [5.0 Lite](seedream-5-0-lite-icodeeasy/SKILL.md) |
| Seedream 4 | [4.5](seedream-4-5-icodeeasy/SKILL.md) · [4.0](seedream-4-0-icodeeasy/SKILL.md) |
| FLUX 2 | [Pro](flux-2-pro-icodeeasy/SKILL.md) · [Max](flux-2-max-icodeeasy/SKILL.md) · [Flex](flux-2-flex-icodeeasy/SKILL.md) |
| FLUX 3 | [Image](flux-3-image-icodeeasy/SKILL.md) · [Image Klein](flux-3-image-klein-icodeeasy/SKILL.md) |

例如，使用 `$image26-sunburst-icodeeasy 生成一张咖啡杯产品图` 或 `$image26-gif-flare-icodeeasy 生成一盏轻轻摇晃的灯笼 GIF`。生成后会等待完成、下载并展示图片。静态图片编辑时附上参考图即可。

Image 2.6 静态图片按成功结果收费。Flare 和 Sunburst 的 1K PNG 每张 ¥0.0833，2K 每张 ¥0.294，4K 每张 ¥0.392。2K 和 4K 的参考图使用 PNG、JPEG 或 WebP。

GIF 可以纯文生，也可以附参考图，帧数、帧间隔和尺寸由模型决定。纯文生 GIF 标准价为每个成功结果 ¥0.0833，参考图生成 GIF 按实际用量结算。

以下命令会安装或更新所有图片与 GIF skill 及其共用脚本。下载和解包成功后才覆盖已有文件。

```bash
(
  update_dir=$(mktemp -d) || exit 1
  trap 'rm -rf "$update_dir"' EXIT
  curl -fL https://github.com/iccccceeeeee/skills/archive/refs/heads/main.tar.gz -o "$update_dir/skills.tar.gz" &&
  tar -xzf "$update_dir/skills.tar.gz" -C "$update_dir" &&
  for skill_dir in "$update_dir"/skills-main/icodeeasy-image-generations \
                   "$update_dir"/skills-main/image*-icodeeasy \
                   "$update_dir"/skills-main/seedream*-icodeeasy \
                   "$update_dir"/skills-main/flux*-icodeeasy; do
    skill_name=${skill_dir##*/}
    mkdir -p "$HOME/.codex/skills/$skill_name" &&
    cp -R "$skill_dir/." "$HOME/.codex/skills/$skill_name/" || exit 1
  done
)
```

旧版安装更新后，可删除 `~/.codex/skills/` 下 `image25-icodeeasy`、`image26-icodeeasy`、`image26-gif-icodeeasy`、`seedream-icodeeasy` 和 `flux-icodeeasy` 各目录中的 `SKILL.md`。目录里的其他文件可保留。重启 Codex 后，旧入口会从技能列表消失。

配置 API Key 后，在新聊天中直接调用对应 skill。

```bash
export OPENAI_API_KEY="<your-api-key>"
```

认证也兼容 `ANTHROPIC_AUTH_TOKEN`。图片与下载输出放在项目的 `out/images/`。图片结果链接长期有效，按敏感信息处理。

[icodeeasy-image-generations](icodeeasy-image-generations/SKILL.md) 是通用生图入口，未指定模型时使用 Image 2。指定 Image 2.5 或 2.6 而未指定变体时，默认使用对应版本的 Flare。

### `icodeeasy-video-generations`

通过 iCodeEasy Video API 创建、轮询、下载或删除异步视频任务。

安装到 Codex：

```bash
if [ -d ~/.codex/skills/icodeeasy-video-generations ]; then echo "icodeeasy-video-generations 已安装"; else mkdir -p ~/.codex/skills && curl -L https://github.com/iccccceeeeee/skills/archive/refs/heads/main.tar.gz | tar -xz -C ~/.codex/skills --strip-components=1 skills-main/icodeeasy-video-generations; fi
```

安装或更新后，重启 Codex，让它重新发现 skill。

配置 API Key：

```bash
export OPENAI_API_KEY="<your-api-key>"
```

在 Codex 中调用 `$icodeeasy-video-generations` 并描述要生成的视频。创建任务会产生付费调用；只在用户明确授权后使用 `--confirm-paid`，不确定时先用 `--dry-run`。视频与临时下载保存在 `out/`，默认不提交。

已安装用户需要更新：上面的安装命令在目录存在时会直接跳过。下面的命令下载并校验解包成功后，覆盖视频 skill 的仓库文件；保留本地额外文件。完成后重启 Codex。

```bash
(
  update_dir=$(mktemp -d) || exit 1
  trap 'rm -rf "$update_dir"' EXIT
  curl -fL https://github.com/iccccceeeeee/skills/archive/refs/heads/main.tar.gz -o "$update_dir/skills.tar.gz" &&
  tar -xzf "$update_dir/skills.tar.gz" -C "$update_dir" skills-main/icodeeasy-video-generations &&
  mkdir -p ~/.codex/skills/icodeeasy-video-generations &&
  cp -R "$update_dir/skills-main/icodeeasy-video-generations/." ~/.codex/skills/icodeeasy-video-generations/
)
```

下载前先创建输出目录，例如 `mkdir -p ./out`。查询或下载失败不代表生成失败。保留任务 ID，用 `video_task.py poll` 或 `download` 恢复原任务；也可在 API Key 所属账号的[日志明细](https://icodeeasy.cc/dashboard/logs/)预览、下载已成功的视频。不要因此重新生成。
