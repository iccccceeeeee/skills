# Task 6 report: MiniMax H3 and Grok video commands

## Scope

- Added independent immutable `MODEL_SPEC` entrypoints for `MiniMax-H3` and
  `grok-imagine-1.5-video`.
- Added focused public-contract tests for both commands.
- Used only `StandardModelSpec` and `run_standard_model`; no model capability
  data was added to `_video_common.py`, and no Kling Task 7 file was changed.

## TDD evidence

### RED

Both focused tests were written before either entrypoint existed, then run:

```sh
python -m unittest \
  icodeeasy-video-generations/tests/test_minimax_h3.py \
  icodeeasy-video-generations/tests/test_grok_imagine_1_5_video.py
```

Result: `FAILED (errors=2)`, with the expected missing-entrypoint errors:

```text
ModuleNotFoundError: No module named 'minimax_h3'
ModuleNotFoundError: No module named 'grok_imagine_1_5_video'
```

### GREEN

After adding the two thin model scripts, the same focused command passed:

```text
Ran 8 tests in 0.247s
OK
```

The expected argparse diagnostics for invalid public options are emitted on
stderr while the suite passes. The eighth Grok reference is rejected during
shared payload validation, where the runner enforces `max_reference_images`.

## Final verification

```sh
TASK6_TEST_PATH=icodeeasy-video-generations/tests PYTHONPATH="$TASK6_TEST_PATH" \
python -m unittest \
  icodeeasy-video-generations/tests/test_common_auth.py \
  icodeeasy-video-generations/tests/test_common_http.py \
  icodeeasy-video-generations/tests/test_common_lifecycle.py \
  icodeeasy-video-generations/tests/test_common_download.py \
  icodeeasy-video-generations/tests/test_video_task_cli.py \
  icodeeasy-video-generations/tests/test_doubao_seedance_2_5.py \
  icodeeasy-video-generations/tests/test_doubao_seedance_2_0.py \
  icodeeasy-video-generations/tests/test_doubao_seedance_2_0_fast.py \
  icodeeasy-video-generations/tests/test_doubao_seedance_2_0_mini.py \
  icodeeasy-video-generations/tests/test_doubao_seedance_1_5_pro.py \
  icodeeasy-video-generations/tests/test_minimax_h3.py \
  icodeeasy-video-generations/tests/test_grok_imagine_1_5_video.py
# Ran 72 tests in 17.176s — OK

python -m py_compile \
  icodeeasy-video-generations/scripts/minimax_h3.py \
  icodeeasy-video-generations/scripts/grok_imagine_1_5_video.py \
  icodeeasy-video-generations/tests/test_minimax_h3.py \
  icodeeasy-video-generations/tests/test_grok_imagine_1_5_video.py
# exited 0
```

The Task 6 files were scanned for `console.log`, `debugger`, `TODO`, and
`HACK`; none were found. `git diff --cached --check` is run before commit.

## Self-review

- MiniMax H3 exposes exactly `768P`/`2K`, its six approved ratios, 4–15
  seconds with a five-second default, and first/last frame roles. It exposes
  neither an audio CLI flag nor a `generate_audio` payload field.
- Grok exposes only the canonical public ID, `480p`/`720p`, five approved
  ratios, 6–30 seconds, and up to seven public HTTPS roleless references. It
  has no frame or audio flags, and neither `--help` nor dry-run JSON can expose
  its supplier-only wire ID.
- Paid confirmation, one-POST/no-retry behavior, caller-visible idempotency,
  JSON output, prompt-file loading, and public HTTPS URL validation stay in the
  approved shared runner.

## Commit

- `Add MiniMax and Grok video commands`
- Author and committer are verified after commit as `iCodeEasy Skills
  <noreply@users.noreply.github.com>`.

## Concerns

None. The repository-wide contract intentionally names later Task 7 scripts
that remain outside Task 6, so it is not a completion gate for this slice.
