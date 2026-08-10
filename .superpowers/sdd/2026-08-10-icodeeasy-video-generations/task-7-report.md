# Task 7: Kling Standard Video Commands

## Scope

- Added five thin `StandardModelSpec` entrypoints for Kling 2.6, 3.0 Turbo,
  V3, V3 Omni, and Video O1.
- Added one focused contract-test module for each entrypoint.
- Kept model-specific cross-field validation in its owning entrypoint; shared
  runner behavior was not changed.
- Motion Control files were deliberately not started.

## RED Evidence

Before the entrypoints existed, each focused test was run with:

```sh
python3 -m unittest discover -s icodeeasy-video-generations/tests -p 'test_kling_v2_6.py' -v
python3 -m unittest discover -s icodeeasy-video-generations/tests -p 'test_kling_v3_0_turbo.py' -v
python3 -m unittest discover -s icodeeasy-video-generations/tests -p 'test_kling_v3.py' -v
python3 -m unittest discover -s icodeeasy-video-generations/tests -p 'test_kling_v3_omni.py' -v
python3 -m unittest discover -s icodeeasy-video-generations/tests -p 'test_kling_video_o1.py' -v
```

Each run failed at import time with the expected `ModuleNotFoundError` for its
missing Kling entrypoint.

## GREEN Evidence

Each focused command above was rerun after its corresponding thin entrypoint:

- Kling 2.6: 3 tests passed.
- Kling 3.0 Turbo: 2 tests passed.
- Kling V3: 2 tests passed.
- Kling V3 Omni: 3 tests passed.
- Kling Video O1: 2 tests passed.

Final shared and standard-model verification:

```sh
python3 -m unittest discover -s icodeeasy-video-generations/tests -p 'test_common_*.py' -v
python3 -m unittest discover -s icodeeasy-video-generations/tests -p 'test_doubao_*.py' -v
python3 -m unittest discover -s icodeeasy-video-generations/tests -p 'test_minimax_h3.py' -v
python3 -m unittest discover -s icodeeasy-video-generations/tests -p 'test_grok_imagine_1_5_video.py' -v
python3 -m unittest discover -s icodeeasy-video-generations/tests -p 'test_kling_*.py' -v
python3 -m py_compile icodeeasy-video-generations/scripts/kling_v2_6.py \\
  icodeeasy-video-generations/scripts/kling_v3_0_turbo.py \\
  icodeeasy-video-generations/scripts/kling_v3.py \\
  icodeeasy-video-generations/scripts/kling_v3_omni.py \\
  icodeeasy-video-generations/scripts/kling_video_o1.py
git diff --check
```

Result: 38 common, 22 Seedance, 4 MiniMax, 4 Grok, and 12 Kling tests passed;
compilation and whitespace validation exited 0.

## Commit

`Add Kling standard video commands`

## Self-review

- All public model IDs are exact: `kling-v2-6`, `kling-3.0-turbo`,
  `kling-v3`, `kling-v3-omni`, and `kling-video-o1`.
- Non-Omni commands expose no roleless `--reference-image` option.
- Omni accepts either roleful first/last frames or up to two roleless references
  and rejects mixed requests before a paid call.
- Kling 2.6 applies its 1080p-only audio and last-frame/audio restrictions
  before request submission.

## Concerns

The repository-wide required-file contract remains intentionally incomplete
until the separately scoped Motion Control task adds its two entrypoints.
