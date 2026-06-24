# Ice Skills

Codex skills for local workflows.

中文版本: [README.md](README.md)

Each skill provides one install command that pulls directly into `~/.codex/skills/`.

## Skills

### `icodeeasy-image-generations`

Generate and edit images with the iCodeEasy OpenAI-compatible Images API.

Install into Codex:

```bash
mkdir -p ~/.codex/skills && npx degit --force iccccceeeeee/skills/icodeeasy-image-generations ~/.codex/skills/icodeeasy-image-generations
```

Restart Codex after installing or updating the skill.

Configure API access:

```bash
export OPENAI_API_KEY="<your-api-key>"
```

Run the script directly:

```bash
python3 ~/.codex/skills/icodeeasy-image-generations/scripts/generate_image.py generate --prompt "a quiet watercolor landscape" --quality low --download-dir ./out/images
```

Edit an image:

```bash
python3 ~/.codex/skills/icodeeasy-image-generations/scripts/generate_image.py edit --prompt "make the lighting softer" --image-file /path/to/reference.png --quality low --download-dir ./out/images
```

Preview the request without sending it:

```bash
python3 ~/.codex/skills/icodeeasy-image-generations/scripts/generate_image.py generate --prompt "minimal product photo" --dry-run --json
```

Do not commit `.env` files, generated images, or output directories. This repository ignores `.env*` and `out/` by default.

This skill does not send `size`. Result URLs are long-lived bearer links, so treat them as sensitive.
