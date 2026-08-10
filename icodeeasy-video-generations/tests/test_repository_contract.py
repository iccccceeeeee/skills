"""Repository-level contract for the iCodeEasy video skill."""

from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOT = REPOSITORY_ROOT / "icodeeasy-video-generations"

EXPECTED_MODEL_SCRIPTS = (
    "doubao_seedance_2_5.py",
    "doubao_seedance_2_0.py",
    "doubao_seedance_2_0_fast.py",
    "doubao_seedance_2_0_mini.py",
    "doubao_seedance_1_5_pro.py",
    "minimax_h3.py",
    "grok_imagine_1_5_video.py",
    "kling_v2_6.py",
    "kling_v3_0_turbo.py",
    "kling_v3.py",
    "kling_v3_omni.py",
    "kling_video_o1.py",
    "kling_v2_6_motion_control.py",
    "kling_v3_motion_control.py",
)


class RepositoryContractTests(unittest.TestCase):
    def test_required_skill_paths_exist(self) -> None:
        required_paths = (
            "SKILL.md",
            "agents/openai.yaml",
            "references/api.md",
            "scripts/_video_common.py",
            "scripts/video_task.py",
            *(f"scripts/{script}" for script in EXPECTED_MODEL_SCRIPTS),
        )

        missing = [path for path in required_paths if not (SKILL_ROOT / path).is_file()]

        self.assertEqual(missing, [])

    def test_tracked_text_has_no_local_or_credential_leaks(self) -> None:
        local_home_prefix = "/" + "Users" + "/"
        local_username = "kurisu" + "code"
        personal_email_domain = "@" + "kurisu" + "amatist" + "." + "com"
        credential_assignment = re.compile(
            r"(?:OPENAI|ANTHROPIC|ICODEEASY)_" + r"API_KEY\s*=",
            re.IGNORECASE,
        )
        forbidden = (local_home_prefix, local_username, personal_email_domain)

        tracked_files = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
        ).stdout.decode().split("\0")

        violations = []
        skill_prefix = "icodeeasy-video-generations/"
        for relative_path in filter(None, tracked_files):
            if not relative_path.startswith(skill_prefix):
                continue
            path = REPOSITORY_ROOT / relative_path
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue

            if any(needle in text for needle in forbidden) or credential_assignment.search(text):
                violations.append(relative_path)

        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
