# Ice Skills

Codex skills for local workflows.

中文版本: [README.md](README.md)

Each skill provides one install command that pulls directly into `~/.codex/skills/`. The install command only depends on common `curl` and `tar` tools.

## Skills

### `icodeeasy-image-generations`

Generate and edit images with the iCodeEasy OpenAI-compatible Images API.

Install into Codex:

```bash
if [ -d ~/.codex/skills/icodeeasy-image-generations ]; then echo "icodeeasy-image-generations is already installed"; else mkdir -p ~/.codex/skills && curl -L https://github.com/iccccceeeeee/skills/archive/refs/heads/main.tar.gz | tar -xz -C ~/.codex/skills --strip-components=1 skills-main/icodeeasy-image-generations; fi
```

Restart Codex after installing or updating the skill.

Configure API access:

```bash
export OPENAI_API_KEY="<your-api-key>"
```

Use:

- In Codex, invoke `$icodeeasy-image-generations`, then describe the image to generate or edit.
- For image edits, provide the reference image path or URL in the same request.

Do not commit `.env` files, generated images, or output directories. This repository ignores `.env*` and `out/` by default.

This skill does not send `size`. Result URLs are long-lived bearer links, so treat them as sensitive.

### `icodeeasy-video-generations`

Create, poll, download, or delete asynchronous video tasks with the iCodeEasy Video API.

Install into Codex:

```bash
if [ -d ~/.codex/skills/icodeeasy-video-generations ]; then echo "icodeeasy-video-generations is already installed"; else mkdir -p ~/.codex/skills && curl -L https://github.com/iccccceeeeee/skills/archive/refs/heads/main.tar.gz | tar -xz -C ~/.codex/skills --strip-components=1 skills-main/icodeeasy-video-generations; fi
```

Restart Codex after installing or updating the skill.

Configure API access:

```bash
export OPENAI_API_KEY="<your-api-key>"
```

In Codex, invoke `$icodeeasy-video-generations` and describe the video to create. Creating a task is a paid API call: use `--confirm-paid` only after explicit user authorization, and use `--dry-run` when unsure. Generated videos and temporary downloads belong in `out/` and are ignored by default.
