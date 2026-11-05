# Ice Skills

Codex skills for local workflows.

中文版本: [README.md](README.md)

Skills install into `~/.codex/skills/`. The commands below use `curl` and `tar`.

## Skills

### Image generation

Choose a standalone skill by version and describe the image you want.

| Skill | Model | Example |
| --- | --- | --- |
| [image2-icodeeasy](image2-icodeeasy/SKILL.md) | Image 2 | `$image2-icodeeasy paint a ginger cat on a windowsill` |
| [image25-icodeeasy](image25-icodeeasy/SKILL.md) | Image 2.5 | `$image25-icodeeasy change the reference background to a beach` |
| [image26-icodeeasy](image26-icodeeasy/SKILL.md) | Image 2.6 | `$image26-icodeeasy create a looping GIF of a swaying lantern` |

Each skill includes its own script and instructions and can be installed independently. Image 2.5 and 2.6 default to Flare; ask for Sunburst to use that variant. Skills wait for completion, download the image, and display it. Include a reference image when requesting a static edit. `image26-icodeeasy` also generates animated GIFs from text, with nine frames at 200 ms per frame by default.

Install or update all three image skills in one command. Existing files are replaced after a successful download and extraction.

```bash
(
  update_dir=$(mktemp -d) || exit 1
  trap 'rm -rf "$update_dir"' EXIT
  curl -fL https://github.com/iccccceeeeee/skills/archive/refs/heads/main.tar.gz -o "$update_dir/skills.tar.gz" &&
  tar -xzf "$update_dir/skills.tar.gz" -C "$update_dir" skills-main/image2-icodeeasy skills-main/image25-icodeeasy skills-main/image26-icodeeasy &&
  for skill_name in image2-icodeeasy image25-icodeeasy image26-icodeeasy; do
    mkdir -p "$HOME/.codex/skills/$skill_name" &&
    cp -R "$update_dir/skills-main/$skill_name/." "$HOME/.codex/skills/$skill_name/" || exit 1
  done
)
```

Configure the API key, then invoke the desired skill in a new chat.

```bash
export OPENAI_API_KEY="<your-api-key>"
```

Authentication also supports `ANTHROPIC_AUTH_TOKEN`. Generated images and downloads belong in the project’s `out/images/`. Treat long-lived result URLs as sensitive.

The original [icodeeasy-image-generations](icodeeasy-image-generations/SKILL.md) name provides an Image 2 compatibility entry.

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
