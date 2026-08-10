# iCodeEasy Video Generations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish an installable `icodeeasy-video-generations` skill with one Python entry script per canonical iCodeEasy video model and safe asynchronous task lifecycle tooling.

**Architecture:** Fourteen model scripts own their model IDs, flags, defaults, and combination rules. A private stdlib-only `_video_common.py` supplies reusable HTTP, authorization, output, idempotency, polling, and download primitives without holding a centralized model capability table; `video_task.py` manages existing task IDs independently. Tests use `unittest`, subprocesses, and local fake HTTP servers only.

**Tech Stack:** Python 3 standard library (`argparse`, `dataclasses`, `http.server`, `json`, `urllib`, `unittest`), Markdown, Agent Skills YAML metadata, Git.

## Global Constraints

- Expose exactly one public script for each of the 14 canonical models listed in the approved design.
- Use `https://api.icodeeasy.cc` as the default base URL.
- Accept only public HTTPS image/video references; do not add local-file, data-URL, `asset_id`, audio-reference, callback, or webhook behavior.
- Trust exactly `api.icodeeasy.cc`, `jp.icodeeasy.cc`, and `sg.icodeeasy.cc` over HTTPS. Require `--trust-custom-base-url` for every other hostname, including lookalike/wildcard subdomains; permit HTTP only for loopback with both `--trust-custom-base-url` and `--allow-insecure-localhost`.
- Require `--confirm-paid` for every networked create/run command; dry-run and existing-task GET/DELETE commands do not require it.
- Send one create POST only. Never automatically retry POST after timeout, disconnect, 5xx, or `submission_unknown`.
- Generate or accept an `Idempotency-Key` of at most 128 characters and make it recoverable without exposing credentials.
- Keep `--json` stdout to one valid JSON document; human progress belongs on stderr.
- Support `--prompt-file` as a shell-history-safe alternative to `--prompt`.
- Use no runtime dependency outside the Python standard library.
- Automated tests must not contact a production endpoint or create a paid task.
- Follow the public documented reference-role contract even where the current server tolerates undocumented roleless non-Omni Kling images.
- Never expose personal names, personal email addresses, API keys, local usernames, or build-machine paths in tracked files or Git metadata.
- Commit with repository-local identity `iCodeEasy Skills <noreply@users.noreply.github.com>`.
- Source contract: `claude-relay-server` commit `7f82730d0b312d1988de0114b441ae971def386c`; catalog/docs last relevant commit `5a6cdb93e1536a45a5225bc88223fd03d30c6cff`.

---

## File map

Create under `icodeeasy-video-generations/`:

- `SKILL.md`: concise routing and paid-call safety workflow.
- `agents/openai.yaml`: Codex display metadata.
- `references/api.md`: shared endpoints, task states, idempotency, errors, and model-script index.
- `scripts/_video_common.py`: generic CLI/HTTP/task primitives and reusable standard/motion spec types.
- `scripts/video_task.py`: `poll`, `download`, and `delete` CLI for existing tasks.
- `scripts/<model_name>.py`: fourteen model-owned entrypoints.
- `tests/fake_video_api.py`: scripted local HTTP server and request recorder.
- `tests/catalog_snapshot.json`: test-only pinned authoritative capability snapshot; never imported by runtime code.
- `tests/test_common_auth.py`, `test_common_http.py`, `test_common_lifecycle.py`, `test_common_download.py`: shared mechanics.
- `tests/test_video_task_cli.py`: existing-task CLI behavior.
- `tests/test_<model_name>.py`: one focused contract test file per model script.
- `tests/test_repository_contract.py`: required file list, metadata, help output, privacy, and README checks.

Modify:

- `README.md`: Chinese install/config/use section.
- `README.en.md`: English equivalent.
- `.gitignore`: ignore Python caches, generated video output, and temporary downloads.

## Task 1: Baseline skill-behavior tests and generated scaffold

**Files:**
- Create: `icodeeasy-video-generations/tests/test_repository_contract.py`
- Create: `icodeeasy-video-generations/` scaffold with the official `init_skill.py`

**Interfaces:**
- Produces: validated skill directory name, `SKILL.md`, `agents/openai.yaml`, `scripts/`, `references/`, and `tests/` locations used by all later tasks.

- [ ] **Step 1: Run three fresh-agent baseline scenarios without the skill**

Use dry-run-only prompts for Seedance first/last frames, Kling Motion Control, and an uncertain paid submission. Record whether the baseline chooses the right model parameters, preserves one task ID, uses idempotency, and avoids retrying POST. The expected RED result is at least one missing deterministic script/parameter contract because the skill does not exist.

- [ ] **Step 2: Write the repository contract test before scaffolding**

Define `EXPECTED_MODEL_SCRIPTS` with the fourteen exact filenames and assert that `SKILL.md`, `agents/openai.yaml`, `references/api.md`, `_video_common.py`, `video_task.py`, and every model entrypoint exist. Assert that tracked text contains no local home-directory prefix, known local username, personal email-domain pattern, or credential assignment. Construct sensitive search needles from fragments inside the test so the forbidden value itself is never committed.

- [ ] **Step 3: Run the repository contract test and observe RED**

Run:

```bash
python3 -m unittest icodeeasy-video-generations/tests/test_repository_contract.py -v
```

Expected: FAIL because the skill files do not exist.

- [ ] **Step 4: Initialize the skill with the official scaffold tool**

Run the installed `skill-creator` `init_skill.py` with:

```text
name=icodeeasy-video-generations
resources=scripts,references
display_name=iCodeEasy Videos
short_description=Generate videos via the iCodeEasy API
default_prompt=Use $icodeeasy-video-generations to generate a video from this request.
```

Create `tests/` separately. Remove generated placeholder/example files that are not used, but do not implement behavior yet.

- [ ] **Step 5: Commit the scaffold and RED contract**

Stage only the new skill scaffold and repository contract test. Commit with subject `Scaffold iCodeEasy video skill tests`.

## Task 2: Shared authentication, HTTP, idempotency, and output primitives

**Files:**
- Create: `icodeeasy-video-generations/tests/fake_video_api.py`
- Create: `icodeeasy-video-generations/tests/test_common_auth.py`
- Create: `icodeeasy-video-generations/tests/test_common_http.py`
- Create: `icodeeasy-video-generations/scripts/_video_common.py`

**Interfaces:**
- Produces: `UserError`, `ProtocolError`, `resolve_api_key() -> tuple[str, str]`, `normalize_base_url(str) -> str`, `new_idempotency_key() -> str`, `request_json(...)`, `emit_result(...)`, and CLI numeric/HTTPS validators.
- `request_json` accepts `method`, `url`, optional `api_key`, optional JSON `payload`, optional headers, and timeout; it performs exactly one request.

- [ ] **Step 1: Write failing auth and dry-run tests**

Cover key priority (`OPENAI_API_KEY` before `ANTHROPIC_AUTH_TOKEN`), missing-key network failure, key-free dry-run, prompt-file loading, and redaction when an HTTP error body echoes the secret.

- [ ] **Step 2: Write failing HTTP/idempotency tests**

Use the fake server to assert Bearer/JSON headers, a caller key sent unchanged, generated keys prefixed `idem_` and no longer than 128 characters, rejection of keys over 128 characters, one POST after disconnect/timeout/502/503, structured JSON/non-JSON errors, valid-JSON-only stdout, exact acceptance of the three official hosts, rejection of lookalike/wildcard hosts without custom trust, custom-host trust gating, loopback-only HTTP gating, and base URL rejection for userinfo/fragments.

Add the recovery sequence: a first POST is accepted by the fake service but its connection drops; no automatic retry occurs; an explicit second invocation with the same key and identical normalized payload returns the original task ID. A third invocation with the same key and a changed payload returns `409 idempotency_conflict` without creating a second task.

- [ ] **Step 3: Run focused tests and verify expected RED imports**

Run:

```bash
python3 -m unittest discover -s icodeeasy-video-generations/tests -p 'test_common_auth.py' -v
python3 -m unittest discover -s icodeeasy-video-generations/tests -p 'test_common_http.py' -v
```

Expected: FAIL because `_video_common.py` is absent.

- [ ] **Step 4: Implement the minimal common primitives**

Use `urllib.request` once per call. Sanitize all displayed error text by replacing the active key with `<redacted>` and redact query strings from signed URLs. Keep JSON output on stdout and human progress/errors on stderr. Generate `idem_<32 lowercase hex characters>` and print it before opening the POST connection in human mode; include it in the single JSON result in JSON mode. On an uncertain result, output the same key and an exact recovery command but do not issue another POST. After a confirmed terminal failure, any replacement create must use a new key and a fresh `--confirm-paid` invocation.

- [ ] **Step 5: Run auth/HTTP tests to GREEN and commit**

Run both focused commands plus `python3 -m py_compile icodeeasy-video-generations/scripts/_video_common.py`. Commit `Add safe video API primitives`.

## Task 3: Existing-task lifecycle and safe download CLI

**Files:**
- Create: `icodeeasy-video-generations/tests/test_common_lifecycle.py`
- Create: `icodeeasy-video-generations/tests/test_common_download.py`
- Create: `icodeeasy-video-generations/tests/test_video_task_cli.py`
- Create: `icodeeasy-video-generations/scripts/video_task.py`
- Modify: `icodeeasy-video-generations/scripts/_video_common.py`

**Interfaces:**
- Produces: `task_url(base_url, task_id, suffix='')`, `poll_task(...)`, `download_task(...)`, `delete_task(...)`.
- `poll_task` returns the last task object and stops only at `succeeded`, `failed`, an unknown status, or max-wait.
- `download_task` writes to a sibling `.part` file and atomically replaces the destination only after successful completion.

- [ ] **Step 1: Write failing task lifecycle tests**

Cover one-shot poll; queued → running → succeeded wait; terminal failed; max-wait; unknown status; URL-encoding a task ID as one path segment; DELETE 204; and `409 video_delete_unsafe` without retry.

- [ ] **Step 2: Write failing download tests**

Cover authenticated 200 and 206 MP4 responses, redirect to a second local origin without forwarding `Authorization`, redirect-count limit, HTTPS-to-HTTP downgrade rejection, truncated/error response preserving an existing destination, private `0600` output mode, and refusal to overwrite until the `.part` file completes unless `--overwrite` is explicit.

- [ ] **Step 3: Run lifecycle/download tests and verify RED**

Run the three new test modules; expected failure is missing lifecycle functions and `video_task.py`.

- [ ] **Step 4: Implement lifecycle functions and CLI**

Expose:

```text
video_task.py poll TASK_ID [--wait --interval 5 --max-wait 900]
video_task.py download TASK_ID --output PATH [--overwrite]
video_task.py delete TASK_ID
```

Use exit `0` for successful operations, `1` for input/auth/HTTP/protocol/terminal/max-wait failures, and argparse's `2` for syntax errors.

- [ ] **Step 5: Run tests to GREEN and commit**

Compile both scripts, run the three focused modules, then commit `Add video task lifecycle commands`.

## Task 4: Standard-model spec runner and Seedance 2.5 reference implementation

**Files:**
- Create: `icodeeasy-video-generations/tests/test_doubao_seedance_2_5.py`
- Create: `icodeeasy-video-generations/scripts/doubao_seedance_2_5.py`
- Modify: `icodeeasy-video-generations/scripts/_video_common.py`

**Interfaces:**
- Produces: immutable `StandardModelSpec`, `build_standard_parser(spec)`, `build_standard_payload(spec, args)`, and `run_standard_model(spec)`.
- `StandardModelSpec` holds canonical ID, resolution/ratio/duration choices and defaults, audio support/default, first/last/reference behavior, and cross-field validation callback.

- [ ] **Step 1: Write failing Seedance 2.5 CLI/payload tests**

Assert default `480p`, `9:16`, 4 seconds, audio true; `720p`/30 seconds accepted; first+last HTTPS content emitted with correct roles and ratio normalized to `adaptive`; `1080p`, 31 seconds, last-only, roleless/data URL, unsupported callback, and network create without `--confirm-paid` rejected.

- [ ] **Step 2: Verify RED**

Run the model test; expected failure is absent parser/spec/script.

- [ ] **Step 3: Implement the generic standard runner and model script**

The model file defines only its immutable `MODEL_SPEC` and a small `main()` call. The common runner exposes `create` and `run`, requires non-empty prompt from `--prompt` or `--prompt-file`, supports first/last/reference image flags according to `MODEL_SPEC`, requires `--confirm-paid` before network create, sends one POST, polls the returned `id` for `run`, and optionally downloads with `--output`.

- [ ] **Step 4: Run tests to GREEN and commit**

Run the Seedance 2.5 and all common tests. Commit `Add Seedance 2.5 video command`.

## Task 5: Remaining Seedance model scripts

**Files:**
- Create: four `tests/test_doubao_seedance_*.py` files for 2.0, 2.0 Fast, 2.0 Mini, and 1.5 Pro.
- Create: matching four scripts under `icodeeasy-video-generations/scripts/`.

**Interfaces:**
- Consumes: `StandardModelSpec` and `run_standard_model` from Task 4.
- Produces: four independent model entrypoints with no shared centralized capability table.

- [ ] **Step 1: Write all four failing model tests**

Lock these distinctions:

- 2.0: `480p/720p/1080p/4K`, 4–15 seconds, adaptive ratio, audio default true.
- 2.0 Fast: `480p/720p`, 4–15 seconds; reject 1080p and roleless references.
- 2.0 Mini: `480p/720p`, 4–15 seconds; reject data URLs and last-only frames.
- 1.5 Pro: `480p/720p/1080p`, 4–12 seconds, no adaptive/4K.

- [ ] **Step 2: Run each test and observe RED for its missing script**

- [ ] **Step 3: Add one minimal `SPEC` script at a time and rerun its test**

Do not add one model's values to another model file or to `_video_common.py`.

- [ ] **Step 4: Run the five Seedance tests together and commit**

Commit `Add remaining Seedance video commands`.

## Task 6: MiniMax H3 and Grok scripts

**Files:**
- Create: `tests/test_minimax_h3.py`, `tests/test_grok_imagine_1_5_video.py`.
- Create: `scripts/minimax_h3.py`, `scripts/grok_imagine_1_5_video.py`.

**Interfaces:**
- Consumes: Task 4 standard runner.
- Produces: two independent model entrypoints.

- [ ] **Step 1: Write failing MiniMax H3 tests**

Assert `768P/2K`, default 5 seconds, 4–15 seconds, six ratios, first/last roles, case-sensitive `2K`, and complete absence of generated-audio flags/payload.

- [ ] **Step 2: Write failing Grok tests**

Assert public model ID `grok-imagine-1.5-video`, `480p/720p`, 6–30 seconds, five ratios, up to seven unordered HTTPS reference images, and rejection of frame roles/audio/5 seconds/eighth image. Assert no supplier wire ID appears in help or output.

- [ ] **Step 3: Verify RED, implement both scripts, and verify GREEN**

- [ ] **Step 4: Commit**

Commit `Add MiniMax and Grok video commands`.

## Task 7: Kling standard-model scripts

**Files:**
- Create: five `tests/test_kling_*.py` files for v2.6, 3.0 Turbo, v3, v3 Omni, and Video O1.
- Create: matching five scripts.

**Interfaces:**
- Consumes: Task 4 standard runner plus per-model cross-field validation callbacks defined in each Kling script.
- Produces: five independent Kling entrypoints.

- [ ] **Step 1: Write failing per-model tests**

Lock these special cases:

- v2.6: 5/10 seconds; audio only at 1080p; last frame requires 1080p and disables audio.
- 3.0 Turbo: 3–15 seconds; first frame only; no audio.
- v3: 3–15 seconds; `720p/1080p/4K`; first/last; audio default true.
- v3 Omni: roleful first/last or up to two roleless references, never mixed; audio default true.
- Video O1: 5/10 seconds; first/last; no audio.

For non-Omni scripts, reject undocumented roleless references even though current server validation is permissive.

- [ ] **Step 2: Run each test and observe RED**

- [ ] **Step 3: Implement one model script at a time and rerun its focused test**

- [ ] **Step 4: Run all common + standard model tests and commit**

Commit `Add Kling standard video commands`.

## Task 8: Kling Motion Control scripts

**Files:**
- Create: `tests/test_kling_v2_6_motion_control.py`, `tests/test_kling_v3_motion_control.py`.
- Create: `scripts/kling_v2_6_motion_control.py`, `scripts/kling_v3_motion_control.py`.
- Modify: `scripts/_video_common.py`.

**Interfaces:**
- Produces: immutable `MotionModelSpec`, `build_motion_parser(spec)`, `build_motion_payload(spec, args)`, and `run_motion_model(spec)`.

- [ ] **Step 1: Write failing Motion Control tests**

Require exactly one HTTPS reference image and one HTTPS reference video; accept `std/pro`, `image/video`, optional prompt, and `--keep-original-sound/--no-keep-original-sound`; default to `std`, `image`, and true. Verify that resolution, ratio, duration, generated audio, first-frame, and last-frame flags are absent/rejected. Do not attempt client-side media-duration probing.

- [ ] **Step 2: Verify RED**

- [ ] **Step 3: Implement generic motion runner and the two thin model scripts**

Assert each script's canonical ID independently so v3 cannot accidentally route as v2.6.

- [ ] **Step 4: Run Motion + common lifecycle tests and commit**

Commit `Add Kling motion control commands`.

## Task 9: Skill instructions, API reference, metadata, and repository docs

**Files:**
- Modify: `icodeeasy-video-generations/SKILL.md`
- Create/Modify: `icodeeasy-video-generations/references/api.md`
- Modify: `icodeeasy-video-generations/agents/openai.yaml`
- Modify: `README.md`, `README.en.md`, `.gitignore`
- Modify: `icodeeasy-video-generations/tests/test_repository_contract.py`
- Create: `icodeeasy-video-generations/tests/catalog_snapshot.json`

**Interfaces:**
- Produces: discoverable skill metadata, correct script routing, install command, credential setup, and safe paid-call instructions.

- [ ] **Step 1: Extend repository/documentation contract tests and verify RED**

Assert YAML names/display strings, README install paths, all 14 model-script names in the API reference, `--confirm-paid` safety wording, idempotency/retry guidance, and no personal/build-machine metadata. Load every script's `MODEL_SPEC` and compare its canonical public fields to the pinned `catalog_snapshot.json`; runtime code must not import the snapshot.

- [ ] **Step 2: Write the minimal skill instructions and API reference**

Route users to the exact model script, require explicit paid authorization, prefer `run` for create→same-task polling, and direct existing task work to `video_task.py`. Keep detailed flags in each script's `--help` rather than duplicating all combinations in `SKILL.md`.

- [ ] **Step 3: Generate `agents/openai.yaml` with the official tool**

Use the exact interface values from Task 1 and validate the generated file.

- [ ] **Step 4: Update Chinese/English READMEs and ignore rules**

Match the image skill's non-destructive installer. Ignore `__pycache__/`, `*.pyc`, `.env*`, `out/`, `*.part`, and generated MP4 files without ignoring source/test fixtures.

- [ ] **Step 5: Run docs/schema checks to GREEN and commit**

Run the repository contract, official skill validator, and repository docs checker. Commit `Document iCodeEasy video skill`.

## Task 10: Full verification, independent forward tests, privacy audit, and publication

**Files:**
- Modify only files required to fix verified failures.

**Interfaces:**
- Produces: validated Git history and pushed `origin/main` containing the design plus implementation commits.

- [ ] **Step 1: Run the complete local suite**

```bash
python3 -m unittest discover -s icodeeasy-video-generations/tests -p 'test_*.py' -v
python3 -m compileall -q icodeeasy-video-generations/scripts icodeeasy-video-generations/tests
```

- [ ] **Step 2: Run every entrypoint's help and dry-run smoke**

Invoke `--help` for all 14 model scripts and `video_task.py`. Run one default dry-run for every standard model and one valid dry-run for each Motion Control model. No command may contact the network.

- [ ] **Step 3: Run official skill and docs validation**

Run `quick_validate.py` against `icodeeasy-video-generations` and `check_repo_docs.py --root .`. Inspect actual exit codes and output.

- [ ] **Step 4: Run independent fresh-agent forward tests with the completed skill**

Use five scenarios: Seedance text, Seedance first/last, Grok seven references, Kling Motion Control, and uncertain submission. Restrict execution to dry-run or local fake base URL. Confirm correct script selection, parameters, same-task polling, and no automatic POST retry.

- [ ] **Step 5: Audit secrets, identities, paths, and Git metadata**

Search the outgoing tree and `origin/main..HEAD` diff for API-key patterns, personal email addresses, local home-directory prefixes, local usernames, generated media, environment files, and supplier-only Grok IDs in public surfaces. Verify every outgoing commit uses the configured neutral noreply author and committer identity.

- [ ] **Step 6: Review Git boundary and push safely**

Fetch `origin`, inspect divergence, ensure the worktree is clean, and rerun relevant verification if `origin/main` advanced. Push normally to `origin/main`; never force. Verify the remote SHA and GitHub tree after push.
