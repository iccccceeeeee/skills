# Ice Skills

Small Codex skills for repeatable local workflows.

## Included skills

- `icodeeasy-image-generations`: generate and edit images with the iCodeEasy OpenAI-compatible Images API.

## Install

Clone the repository:

```bash
git clone git@github.com:iccccceeeeee/skills.git ice-skills
cd ice-skills
```

Install the skill by symlinking it into the Codex skills directory:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
ln -s "$PWD/icodeeasy-image-generations" \
  "${CODEX_HOME:-$HOME/.codex}/skills/icodeeasy-image-generations"
```

If you prefer copying instead of symlinking:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R "$PWD/icodeeasy-image-generations" \
  "${CODEX_HOME:-$HOME/.codex}/skills/icodeeasy-image-generations"
```

Restart Codex after installing or updating a skill so the skill metadata can be discovered.

## Configure image API access

Set an API key in your shell environment:

```bash
export OPENAI_API_KEY="<your-api-key>"
```

Do not commit `.env` files or generated image outputs. This repository ignores `.env*` and `out/` directories by default.

## Use the image skill script directly

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

The skill intentionally does not send a `size` parameter. Result URLs returned by the API are long-lived bearer links, so treat them as sensitive.
