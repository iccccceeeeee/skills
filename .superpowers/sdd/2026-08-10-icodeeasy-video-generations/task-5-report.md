# Task 5 report: remaining Seedance video commands

## Scope

- Added four independent immutable `MODEL_SPEC` entrypoints:
  `doubao_seedance_2_0.py`, `doubao_seedance_2_0_fast.py`,
  `doubao_seedance_2_0_mini.py`, and `doubao_seedance_1_5_pro.py`.
- Added one focused contract module for each model.
- Used only the approved `StandardModelSpec` / `run_standard_model` runner;
  no capability values were added to `_video_common.py` and no Task 6 file was
  created or changed.

## TDD evidence

### RED

Each model test was written before its model script. The following commands
each failed with the expected missing-module `ModuleNotFoundError`:

```sh
python3 -m unittest icodeeasy-video-generations/tests/test_doubao_seedance_2_0.py
python3 -m unittest icodeeasy-video-generations/tests/test_doubao_seedance_2_0_fast.py
python3 -m unittest icodeeasy-video-generations/tests/test_doubao_seedance_2_0_mini.py
python3 -m unittest icodeeasy-video-generations/tests/test_doubao_seedance_1_5_pro.py
```

### GREEN

After adding each corresponding thin entrypoint, its focused test passed:

```sh
python3 -m unittest icodeeasy-video-generations/tests/test_doubao_seedance_2_0.py
# Ran 3 tests — OK
python3 -m unittest icodeeasy-video-generations/tests/test_doubao_seedance_2_0_fast.py
# Ran 2 tests — OK
python3 -m unittest icodeeasy-video-generations/tests/test_doubao_seedance_2_0_mini.py
# Ran 2 tests — OK
python3 -m unittest icodeeasy-video-generations/tests/test_doubao_seedance_1_5_pro.py
# Ran 2 tests — OK
```

The expected argparse diagnostics for rejected options were emitted on stderr
while those focused suites passed.

## Final verification

```sh
python3 -m unittest \
  icodeeasy-video-generations/tests/test_doubao_seedance_2_5.py \
  icodeeasy-video-generations/tests/test_doubao_seedance_2_0.py \
  icodeeasy-video-generations/tests/test_doubao_seedance_2_0_fast.py \
  icodeeasy-video-generations/tests/test_doubao_seedance_2_0_mini.py \
  icodeeasy-video-generations/tests/test_doubao_seedance_1_5_pro.py
# Ran 18 tests in 0.201s — OK

python3 -m unittest discover -s icodeeasy-video-generations/tests -p 'test_common_*.py'
# Ran 38 tests in 13.609s — OK

python3 -m py_compile \
  icodeeasy-video-generations/scripts/doubao_seedance_2_0.py \
  icodeeasy-video-generations/scripts/doubao_seedance_2_0_fast.py \
  icodeeasy-video-generations/scripts/doubao_seedance_2_0_mini.py \
  icodeeasy-video-generations/scripts/doubao_seedance_1_5_pro.py \
  icodeeasy-video-generations/tests/test_doubao_seedance_2_0.py \
  icodeeasy-video-generations/tests/test_doubao_seedance_2_0_fast.py \
  icodeeasy-video-generations/tests/test_doubao_seedance_2_0_mini.py \
  icodeeasy-video-generations/tests/test_doubao_seedance_1_5_pro.py

git diff --check
```

`py_compile` and `git diff --check` both exited 0. The changed Python files
were also scanned for `console.log`, `debugger`, `TODO`, and `HACK`; none were
found.

## Self-review

- 2.0 isolates 480p/720p/1080p/4K, 4–15 seconds, adaptive ratio, and audio
  enabled by default.
- 2.0 Fast isolates 480p/720p, 4–15 seconds, and assigns an explicit
  `reference_image` role.
- 2.0 Mini isolates 480p/720p, 4–15 seconds, public HTTPS-only frames, and
  rejects a last-frame-only request.
- 1.5 Pro isolates 480p/720p/1080p, 4–12 seconds, and excludes both 4K and
  adaptive ratio.
- All scripts keep paid-confirmation, no-retry/idempotency, JSON output, and
  public HTTPS reference validation in the approved common runner.

## Commit

- `Add remaining Seedance video commands` (verified with `git show` after the
  final amend)
- Author and committer verified as `iCodeEasy Skills
  <noreply@users.noreply.github.com>`.

## Concerns

None. The repository-wide contract still lists later Task 6+ scripts that are
outside this task, so it was not used as a Task 5 completion gate.

---

## Fix round 1/5: Mini and 1.5 Pro contract coverage

### Added coverage

- Seedance 2.0 Mini now explicitly rejects 1080p, 3- and 16-second requests,
  and `--generate-audio`; its valid payload is asserted not to contain
  `generate_audio`.
- Seedance 1.5 Pro now explicitly rejects first frame, last frame, and
  reference image options; its standard payload is asserted not to contain
  `content`.
- No production behavior changed: these tests lock the existing model specs.

### Focused verification

```sh
python3 -m unittest \
  icodeeasy-video-generations/tests/test_doubao_seedance_2_0_mini.py \
  icodeeasy-video-generations/tests/test_doubao_seedance_1_5_pro.py
```

Result: `Ran 8 tests in 0.003s` — `OK`.

### Mutation check

The Mini `MODEL_SPEC` was temporarily mutated with `supports_audio=True` and
`default_audio=True`, then its focused test was executed:

```sh
python3 -m unittest icodeeasy-video-generations/tests/test_doubao_seedance_2_0_mini.py
```

Result: failed as required with two failures: `--generate-audio` no longer
raised `SystemExit`, and the valid payload unexpectedly contained
`generate_audio: True`. The mutation was reverted using `apply_patch` before
the final verification and commit.

### Final verification

The amended-commit verification reran the five Seedance test modules, the
`test_common_*.py` suite, `py_compile` for all changed files, and
`git diff HEAD~1 HEAD --check`.
