# Ice Skills

Codex skills for local workflows.

## 中文

### 包含的 skill

- `icodeeasy-image-generations`，通过 iCodeEasy 的 OpenAI 兼容 Images API 生成和编辑图片。

### 安装

```bash
git clone git@github.com:iccccceeeeee/skills.git
cd skills
mkdir -p ~/.codex/skills
ln -s "$PWD/icodeeasy-image-generations" ~/.codex/skills/
```

如果不想用软链接，可以复制：

```bash
mkdir -p ~/.codex/skills
cp -R icodeeasy-image-generations ~/.codex/skills/
```

安装或更新后，重启 Codex，让它重新发现 skill。

### 配置 API Key

```bash
export OPENAI_API_KEY="<your-api-key>"
```

不要提交 `.env` 文件、生成图片或输出目录。本仓库默认忽略 `.env*` 和 `out/`。

### 直接运行脚本

生成图片：

```bash
python3 icodeeasy-image-generations/scripts/generate_image.py generate \
  --prompt "a quiet watercolor landscape" \
  --quality low \
  --download-dir ./out/images
```

编辑图片：

```bash
python3 icodeeasy-image-generations/scripts/generate_image.py edit \
  --prompt "make the lighting softer" \
  --image-file /path/to/reference.png \
  --quality low \
  --download-dir ./out/images
```

只看请求，不发送：

```bash
python3 icodeeasy-image-generations/scripts/generate_image.py generate \
  --prompt "minimal product photo" \
  --dry-run \
  --json
```

这个 skill 不发送 `size` 参数。API 返回的结果 URL 长期有效，持有链接的人可以访问图片，请按敏感信息处理。

## English

### Included skill

- `icodeeasy-image-generations`: generate and edit images with the iCodeEasy OpenAI-compatible Images API.

### Install

```bash
git clone git@github.com:iccccceeeeee/skills.git
cd skills
mkdir -p ~/.codex/skills
ln -s "$PWD/icodeeasy-image-generations" ~/.codex/skills/
```

Copy instead of symlink:

```bash
mkdir -p ~/.codex/skills
cp -R icodeeasy-image-generations ~/.codex/skills/
```

Restart Codex after installing or updating the skill.

### Configure API access

```bash
export OPENAI_API_KEY="<your-api-key>"
```

Do not commit `.env` files, generated images, or output directories. This repository ignores `.env*` and `out/` by default.

### Run the script directly

Generate an image:

```bash
python3 icodeeasy-image-generations/scripts/generate_image.py generate \
  --prompt "a quiet watercolor landscape" \
  --quality low \
  --download-dir ./out/images
```

Edit an image:

```bash
python3 icodeeasy-image-generations/scripts/generate_image.py edit \
  --prompt "make the lighting softer" \
  --image-file /path/to/reference.png \
  --quality low \
  --download-dir ./out/images
```

Preview the request without sending it:

```bash
python3 icodeeasy-image-generations/scripts/generate_image.py generate \
  --prompt "minimal product photo" \
  --dry-run \
  --json
```

This skill does not send `size`. Result URLs are long-lived bearer links, so treat them as sensitive.
