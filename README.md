# Ice Skills

Codex skills for local workflows.

English version: [README.en.md](README.en.md)

Skills 安装到 `~/.codex/skills/`。下面的安装命令使用 `curl` 和 `tar`。

## Skills

### 图片生成

选择静态图片或 GIF 的独立 skill，直接描述想要的画面。

| Skill | 模型 | 调用示例 |
| --- | --- | --- |
| [image2-icodeeasy](image2-icodeeasy/SKILL.md) | Image 2 | `$image2-icodeeasy 画一只窗台上的橘猫` |
| [image25-icodeeasy](image25-icodeeasy/SKILL.md) | Image 2.5 | `$image25-icodeeasy 把参考图背景改成海边` |
| [image26-icodeeasy](image26-icodeeasy/SKILL.md) | Image 2.6 静态图片 | `$image26-icodeeasy 生成一张咖啡杯产品图` |
| [image26-gif-icodeeasy](image26-gif-icodeeasy/SKILL.md) | Image 2.6 GIF | `$image26-gif-icodeeasy 生成一盏轻轻摇晃的灯笼 GIF` |

每个 skill 包含独立脚本和说明，可单独安装。Image 2.5、2.6 默认使用 Flare，指定 Sunburst 时会切换对应模型。生成后会等待完成、下载并展示图片。静态图片编辑时附上参考图即可。

Image 2.6 静态图片支持 1K、2K 和 4K。GIF 仅支持文字生成，帧数、帧间隔和尺寸由模型决定。Flare 和 Sunburst 的 1K PNG 和 GIF 每个成功结果 ¥0.0833，2K 和 4K PNG 按实际用量结算。

一次安装或更新四个图片与 GIF skill，下载和解包成功后才覆盖已有文件。

```bash
(
  update_dir=$(mktemp -d) || exit 1
  trap 'rm -rf "$update_dir"' EXIT
  curl -fL https://github.com/iccccceeeeee/skills/archive/refs/heads/main.tar.gz -o "$update_dir/skills.tar.gz" &&
  tar -xzf "$update_dir/skills.tar.gz" -C "$update_dir" skills-main/image2-icodeeasy skills-main/image25-icodeeasy skills-main/image26-icodeeasy skills-main/image26-gif-icodeeasy &&
  for skill_name in image2-icodeeasy image25-icodeeasy image26-icodeeasy image26-gif-icodeeasy; do
    mkdir -p "$HOME/.codex/skills/$skill_name" &&
    cp -R "$update_dir/skills-main/$skill_name/." "$HOME/.codex/skills/$skill_name/" || exit 1
  done
)
```

配置 API Key 后，在新聊天中直接调用对应 skill。

```bash
export OPENAI_API_KEY="<your-api-key>"
```

认证也兼容 `ANTHROPIC_AUTH_TOKEN`。图片与下载输出放在项目的 `out/images/`。图片结果链接长期有效，按敏感信息处理。

原名称 [icodeeasy-image-generations](icodeeasy-image-generations/SKILL.md) 提供 Image 2 兼容入口。

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
