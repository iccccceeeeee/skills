"""Repository-level contract for the iCodeEasy video skill."""

from __future__ import annotations

import re
import subprocess
import unittest
import importlib.util
import json
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

EXPECTED_INTERFACE = {
    "display_name": "iCodeEasy Videos",
    "short_description": "Generate videos via the iCodeEasy API",
    "default_prompt": "Use $icodeeasy-video-generations to generate a video from this request.",
}


def load_model_spec(script_name: str):
    script_path = SKILL_ROOT / "scripts" / script_name
    module_spec = importlib.util.spec_from_file_location(script_path.stem, script_path)
    assert module_spec is not None and module_spec.loader is not None
    module = importlib.util.module_from_spec(module_spec)
    import sys

    scripts_dir = str(script_path.parent)
    sys.path.insert(0, scripts_dir)
    try:
        module_spec.loader.exec_module(module)
    finally:
        sys.path.remove(scripts_dir)
    return module.MODEL_SPEC


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
        supplier_only_grok_id = "grok-imagine-1.5-video-" + "apimart"
        forbidden = (
            local_home_prefix,
            local_username,
            personal_email_domain,
            supplier_only_grok_id,
        )

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
            if "/tests/" in relative_path:
                continue
            path = REPOSITORY_ROOT / relative_path
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue

            if any(needle in text for needle in forbidden) or credential_assignment.search(text):
                violations.append(relative_path)

        self.assertEqual(violations, [])

    def test_public_metadata_and_repository_docs_are_complete(self) -> None:
        metadata = (SKILL_ROOT / "agents/openai.yaml").read_text(encoding="utf-8")
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        api_reference = (SKILL_ROOT / "references/api.md").read_text(encoding="utf-8")
        readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
        readme_en = (REPOSITORY_ROOT / "README.en.md").read_text(encoding="utf-8")
        ignore_rules = (REPOSITORY_ROOT / ".gitignore").read_text(encoding="utf-8")

        self.assertIn("name: icodeeasy-video-generations", skill)
        self.assertNotIn("[TODO:", skill)
        for key, value in EXPECTED_INTERFACE.items():
            self.assertIn(f'{key}: "{value}"', metadata)
        for script_name in EXPECTED_MODEL_SCRIPTS:
            self.assertIn(f"scripts/{script_name}", api_reference)
        for text in (skill, api_reference):
            self.assertIn("--confirm-paid", text)
        self.assertIn("Idempotency-Key", api_reference)
        self.assertRegex(api_reference, r"(?i)do not automatically retry.*POST")
        self.assertIn("run", skill)
        self.assertIn("video_task.py", skill)
        for text in (readme, readme_en):
            self.assertIn("icodeeasy-video-generations", text)
            self.assertIn("skills-main/icodeeasy-video-generations", text)
            self.assertIn("OPENAI_API_KEY", text)
        for rule in ("**/__pycache__/", "*.pyc", ".env*", "**/out/", "*.part", "**/out/*.mp4"):
            self.assertIn(rule, ignore_rules)

    def test_model_specs_match_pinned_public_catalog_snapshot(self) -> None:
        snapshot_path = SKILL_ROOT / "tests/catalog_snapshot.json"
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        self.assertEqual(snapshot["source_catalog"], "video-relay/internal/capability/catalog.json")
        self.assertEqual(snapshot["source_commit"], "7f82730d0b312d1988de0114b441ae971def386c")
        models = snapshot["models"]
        self.assertEqual(set(models), set(EXPECTED_MODEL_SCRIPTS))

        for script_name, expected in models.items():
            spec = load_model_spec(script_name)
            actual = {
                "canonical_id": spec.canonical_id,
                "resolution_choices": list(getattr(spec, "resolution_choices", ())),
                "default_resolution": getattr(spec, "default_resolution", None),
                "ratio_choices": list(getattr(spec, "ratio_choices", ())),
                "default_ratio": getattr(spec, "default_ratio", None),
                "duration_choices": list(getattr(spec, "duration_choices", ())),
                "default_duration": getattr(spec, "default_duration", None),
                "supports_audio": getattr(spec, "supports_audio", False),
                "default_audio": getattr(spec, "default_audio", None),
                "supports_first_frame": getattr(spec, "supports_first_frame", False),
                "supports_last_frame": getattr(spec, "supports_last_frame", False),
                "max_reference_images": getattr(spec, "max_reference_images", 0),
                "form": "motion" if not hasattr(spec, "ratio_choices") else "standard",
            }
            self.assertEqual(actual, expected, script_name)

    def test_catalog_snapshot_has_no_local_or_credential_leaks(self) -> None:
        snapshot = (SKILL_ROOT / "tests/catalog_snapshot.json").read_text(encoding="utf-8")
        local_home_prefix = "/" + "Users" + "/"
        local_username = "kurisu" + "code"
        personal_email_domain = "@" + "kurisu" + "amatist" + ".com"
        supplier_only_grok_id = "grok-imagine-1.5-video-" + "apimart"
        credential_assignment = re.compile(
            r"(?:OPENAI|ANTHROPIC|ICODEEASY)_" + r"API_KEY\s*=",
            re.IGNORECASE,
        )

        self.assertFalse(
            any(
                needle in snapshot
                for needle in (
                    local_home_prefix,
                    local_username,
                    personal_email_domain,
                    supplier_only_grok_id,
                )
            )
        )
        self.assertIsNone(credential_assignment.search(snapshot))

    def test_runtime_does_not_import_test_catalog_snapshot(self) -> None:
        runtime_python = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (SKILL_ROOT / "scripts").glob("*.py")
        )
        self.assertNotIn("catalog_snapshot", runtime_python)


if __name__ == "__main__":
    unittest.main()
