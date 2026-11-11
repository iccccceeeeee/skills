# Ice Skills

Codex skills for local workflows.

中文版本: [README.md](README.md)

Skills install into `~/.codex/skills/`. The commands below use `curl` and `tar`.

## Skills

### Image generation

Choose a skill by model and output format, then describe the result you want.

| Model and output | Skill |
| --- | --- |
| Image 2 | [image2-icodeeasy](image2-icodeeasy/SKILL.md) |
| Image 2.5 static images | [Flare](image25-flare-icodeeasy/SKILL.md) · [Sunburst](image25-sunburst-icodeeasy/SKILL.md) |
| Image 2.6 static images | [Flare](image26-flare-icodeeasy/SKILL.md) · [Sunburst](image26-sunburst-icodeeasy/SKILL.md) |
| Image 2.6 GIF | [Flare](image26-gif-flare-icodeeasy/SKILL.md) · [Sunburst](image26-gif-sunburst-icodeeasy/SKILL.md) |
| Seedream 5 | [5.5](seedream-5-5-icodeeasy/SKILL.md) · [5 Flash](seedream-5-0-flash-icodeeasy/SKILL.md) · [5 Pro](seedream-5-0-pro-icodeeasy/SKILL.md) · [5.0 Lite](seedream-5-0-lite-icodeeasy/SKILL.md) |
| Seedream 4 | [4.5](seedream-4-5-icodeeasy/SKILL.md) · [4.0](seedream-4-0-icodeeasy/SKILL.md) |
| FLUX 2 | [Pro](flux-2-pro-icodeeasy/SKILL.md) · [Max](flux-2-max-icodeeasy/SKILL.md) · [Flex](flux-2-flex-icodeeasy/SKILL.md) |
| FLUX 3 | [Image](flux-3-image-icodeeasy/SKILL.md) · [Image Klein](flux-3-image-klein-icodeeasy/SKILL.md) |

Try `$image26-sunburst-icodeeasy create a coffee cup product photo` or `$image26-gif-flare-icodeeasy create a looping GIF of a swaying lantern`. The skills wait for completion, download the result, and display it. Include a reference image when requesting a static edit.

For both Image 2.6 variants, each successful PNG costs ¥0.0833 at 1K, ¥0.294 at 2K, or ¥0.392 at 4K. Use PNG, JPEG, or WebP reference images at 2K and 4K.

GIFs support text prompts with optional reference images. The model sets frame count, timing, and dimensions. The standard price for a successful text-only GIF is ¥0.0833. GIFs generated with reference images are billed by actual usage.

Install or update all image and GIF skills and their shared scripts. The command replaces existing files after a successful download and extraction.

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

After updating an older installation, you can remove just the `SKILL.md` files from `image25-icodeeasy`, `image26-icodeeasy`, `image26-gif-icodeeasy`, `seedream-icodeeasy`, and `flux-icodeeasy` under `~/.codex/skills/`. You can keep any other files in those directories. Restart Codex to refresh the skill list.

Configure the API key, then invoke the desired skill in a new chat.

```bash
export OPENAI_API_KEY="<your-api-key>"
```

Authentication also supports `ANTHROPIC_AUTH_TOKEN`. Generated images and downloads belong in the project’s `out/images/`. Treat long-lived result URLs as sensitive.

The general [icodeeasy-image-generations](icodeeasy-image-generations/SKILL.md) skill defaults to Image 2 when you leave the model unspecified. If you ask for Image 2.5 or 2.6 without naming a variant, it uses Flare for that version.

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

Existing installations need an update: the installation command above skips a directory that already exists. This downloads and successfully extracts the archive before replacing repository files in the video skill, while preserving additional local files. Restart Codex afterward.

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

A polling or download error does not prove generation failed. Keep the task ID and recover the same task with `video_task.py poll` or `download`. Successful videos are also available in the API Key owner's [usage details](https://icodeeasy.cc/dashboard/logs/). Create the output directory first, for example with `mkdir -p ./out`; do not create another paid task to recover a file.
