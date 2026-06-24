# Ice Skills

Codex skills for local workflows.

English version: [README.en.md](README.en.md)

每个 skill 都提供一条安装命令，直接拉到 `~/.codex/skills/`。安装命令只依赖常见的 `curl` 和 `tar`。

## Skills

### `icodeeasy-image-generations`

通过 iCodeEasy 的 OpenAI 兼容 Images API 生成和编辑图片。

安装到 Codex：

```bash
mkdir -p ~/.codex/skills && rm -rf ~/.codex/skills/icodeeasy-image-generations && curl -L https://github.com/iccccceeeeee/skills/archive/refs/heads/main.tar.gz | tar -xz -C ~/.codex/skills --strip-components=1 skills-main/icodeeasy-image-generations
```

安装或更新后，重启 Codex，让它重新发现 skill。

配置 API Key：

```bash
export OPENAI_API_KEY="<your-api-key>"
```

直接运行脚本：

```bash
python3 ~/.codex/skills/icodeeasy-image-generations/scripts/generate_image.py generate --prompt "a quiet watercolor landscape" --quality low --download-dir ./out/images
```

编辑图片：

```bash
python3 ~/.codex/skills/icodeeasy-image-generations/scripts/generate_image.py edit --prompt "make the lighting softer" --image-file /path/to/reference.png --quality low --download-dir ./out/images
```

只看请求，不发送：

```bash
python3 ~/.codex/skills/icodeeasy-image-generations/scripts/generate_image.py generate --prompt "minimal product photo" --dry-run --json
```

不要提交 `.env` 文件、生成图片或输出目录。本仓库默认忽略 `.env*` 和 `out/`。

这个 skill 不发送 `size` 参数。API 返回的结果 URL 长期有效，持有链接的人可以访问图片，请按敏感信息处理。
