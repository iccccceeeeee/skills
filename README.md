# Ice Skills

Codex skills for local workflows.

English version: [README.en.md](README.en.md)

每个 skill 都提供一条安装命令，直接拉到 `~/.codex/skills/`。安装命令只依赖常见的 `curl` 和 `tar`。

## Skills

### `icodeeasy-image-generations`

通过 iCodeEasy 的 OpenAI 兼容 Images API 生成和编辑图片。

安装到 Codex：

```bash
if [ -d ~/.codex/skills/icodeeasy-image-generations ]; then echo "icodeeasy-image-generations 已安装"; else mkdir -p ~/.codex/skills && curl -L https://github.com/iccccceeeeee/skills/archive/refs/heads/main.tar.gz | tar -xz -C ~/.codex/skills --strip-components=1 skills-main/icodeeasy-image-generations; fi
```

安装或更新后，重启 Codex，让它重新发现 skill。

配置 API Key：

```bash
export OPENAI_API_KEY="<your-api-key>"
```

使用：

- 在 Codex 里直接说 `$icodeeasy-image-generations`，然后描述要生成或编辑的图片。
- 如果要编辑图片，把参考图路径或 URL 一起给 Codex。

不要提交 `.env` 文件、生成图片或输出目录。本仓库默认忽略 `.env*` 和 `out/`。

这个 skill 不发送 `size` 参数。API 返回的结果 URL 长期有效，持有链接的人可以访问图片，请按敏感信息处理。

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
