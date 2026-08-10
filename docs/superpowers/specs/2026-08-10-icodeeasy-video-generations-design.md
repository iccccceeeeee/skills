# iCodeEasy Video Generations Skill Design

## Goal

Add a public, installable `icodeeasy-video-generations` Codex skill to this repository. The skill must cover every canonical model exposed by the iCodeEasy `/v1/videos/*` API while keeping each model's rules isolated in one model-specific script.

## Public surface

The skill provides one Python entry script per canonical model:

- `doubao_seedance_2_5.py`
- `doubao_seedance_2_0.py`
- `doubao_seedance_2_0_fast.py`
- `doubao_seedance_2_0_mini.py`
- `doubao_seedance_1_5_pro.py`
- `minimax_h3.py`
- `kling_v2_6.py`
- `kling_3_0_turbo.py`
- `kling_v3.py`
- `kling_v3_omni.py`
- `kling_video_o1.py`
- `kling_v2_6_motion_control.py`
- `kling_v3_motion_control.py`
- `grok_imagine_1_5_video.py`

Each model script owns its public flags, defaults, reference-media rules, parameter validation, and canonical model ID. Each script supports:

- `create`: validate and submit one asynchronous task.
- `run`: create one task, poll that same task to a terminal state, and optionally download the MP4.
- `--dry-run`: print the validated request without network access.
- `--json`: emit machine-readable output.
- `--base-url`: override the default `https://api.icodeeasy.cc` base URL.
- `--idempotency-key`: reuse a caller-controlled key when retrying a create request whose outcome is uncertain.
- `--prompt-file`: read a sensitive prompt from a file instead of shell history.

A separate `video_task.py` handles model-independent `poll`, `download`, and `delete` operations for existing task IDs.

## Internal structure

`scripts/_video_common.py` contains only shared mechanics:

- Read credentials from `OPENAI_API_KEY`, falling back to `ANTHROPIC_AUTH_TOKEN`.
- Build authenticated JSON requests.
- Accept only `api.icodeeasy.cc`, `jp.icodeeasy.cc`, and `sg.icodeeasy.cc` as trusted official HTTPS hosts; require explicit trust for every other hostname, and allow insecure HTTP only for explicitly trusted loopback test servers.
- Generate and display an idempotency key before a paid create call when the caller did not provide one.
- Submit exactly one create request without automatic POST retries.
- Poll `queued` and `running` tasks until `succeeded` or `failed`.
- Download authenticated task content with redirect support.
- Delete terminal tasks.
- Normalize CLI and HTTP errors without printing credentials.

The common module does not contain model capability tables or model-specific validation. Shared helpers may validate generic HTTPS media URLs and common scalar types, but each model script decides which fields and combinations it accepts.

Each model script is a thin declarative entrypoint with one immutable model specification plus `main()`. A test-only pinned catalog snapshot detects drift across all fourteen scripts without becoming a runtime capability table.

## Reference media

Follow the current public API contract:

- Accept public HTTPS image and video URLs.
- Support Seedance and Kling first/last frames.
- Support MiniMax H3 first/last frames.
- Support Grok unordered reference images.
- Support Kling Motion Control with one reference image and one reference video.
- Do not invent a local-file upload or data-URL protocol.
- Do not accept reference audio.

## Safety and billing behavior

The skill must make paid-task behavior explicit:

1. Require user authorization before calling the paid create endpoint.
2. Submit one create request and preserve its returned task ID.
3. Poll the accepted task rather than creating concurrent replacements.
4. Never automatically retry a POST after a timeout, disconnect, or `submission_unknown` response.
5. Permit a deliberate retry only with the same caller-visible idempotency key or after a confirmed terminal failure.
6. Treat result URLs and downloaded media as sensitive user artifacts.
7. Require `--confirm-paid` for networked create/run commands; dry-run and existing-task operations remain non-paid.
8. Strip authorization on cross-origin download redirects, reject HTTPS-to-HTTP downgrade, and bound redirect depth.
9. Download through the authenticated task-content route into a private temporary file, then atomically rename without overwriting unless explicitly requested.
10. Recover an uncertain accepted submission only by deliberately repeating the identical normalized request with the same key; a replacement after terminal failure requires a new key and fresh paid confirmation.

## Skill documentation

`SKILL.md` stays concise and routes a request to the correct model script. Detailed common API behavior lives in `references/api.md`; per-model examples and constraints remain close to their model scripts and their `--help` output. `agents/openai.yaml` exposes the skill in Codex.

The repository's Chinese and English READMEs add installation, credential, and invocation instructions matching the existing image skill style.

## Testing

No automated test may submit a paid production generation.

- Run baseline agent scenarios without the skill to identify routing and retry mistakes.
- Write model-script tests before implementation and observe the expected failures.
- Give each model script focused validation and request-payload coverage.
- Test `_video_common.py` against a local fake HTTP server for create, polling, terminal failure, download, delete, HTTP errors, credential redaction, and no automatic POST retry.
- Test custom-base-url trust, loopback-only HTTP, cross-origin redirect credential stripping, redirect downgrade rejection, bounded redirects, private file mode, and atomic no-overwrite behavior.
- Test `video_task.py` independently.
- Run dry-run examples for every model.
- Run the canonical skill validator and verify `agents/openai.yaml` metadata.
- Compare all fourteen declarative model specifications with a pinned test-only snapshot derived from the authoritative service catalog.
- Forward-test the completed skill with fresh agents using text-to-video, first/last-frame, Grok reference-image, Motion Control, and uncertain-submission scenarios. Forward tests must use dry-run or a local fake endpoint.

## Completion criteria

The work is complete when:

- All 14 canonical model scripts exist and expose correct model-specific validation.
- Common lifecycle operations work through the shared private module and `video_task.py`.
- All automated tests and skill validation pass without paid external calls.
- README installation and usage instructions are present in Chinese and English.
- The intended files are committed and pushed to `iccccceeeeee/skills` `main` with no credentials, generated media, or unrelated files.
