"""Exercise each independently installed image skill through its CLI."""

from __future__ import annotations

import base64
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_generate_image import FakeAPI

ROOT = Path(__file__).resolve().parents[2]
VERSIONS = {
    "image2-icodeeasy": "gpt-image-2",
    "image25-icodeeasy": "gpt-image-2.5-flare",
    "image26-icodeeasy": "gpt-image-2.6-flare",
}
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl6lAsAAAAASUVORK5CYII="
)


class StandaloneSkillTests(unittest.TestCase):
    def test_image2_accepts_the_requested_landscape_ratio(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "image2-icodeeasy/scripts/generate_image.py"),
             "generate", "--prompt", "A landscape coffee cup photograph",
             "--aspect-ratio", "16:9", "--dry-run", "--json"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["payload"]["aspect_ratio"], "16:9")

    def test_each_skill_runs_with_only_its_own_installed_directory(self):
        for name, model in VERSIONS.items():
            with self.subTest(skill=name), tempfile.TemporaryDirectory() as temporary:
                destination = Path(temporary) / name
                shutil.copytree(ROOT / name, destination)
                result = subprocess.run(
                    [sys.executable, str(destination / "scripts/generate_image.py"),
                     "generate", "--prompt", "A ceramic cup", "--dry-run", "--json"],
                    cwd=temporary, capture_output=True, text=True, check=True,
                    env={key: value for key, value in os.environ.items()
                         if key not in ("OPENAI_API_KEY", "ANTHROPIC_AUTH_TOKEN", "PYTHONPATH")},
                )
                body = json.loads(result.stdout)
                self.assertEqual(body["payload"]["model"], model)
                self.assertEqual(body["payload"]["image_size"], "1K")
                self.assertEqual(body["payload"]["quality"], "medium" if model == "gpt-image-2" else "auto")

    def test_each_skill_generates_and_edits_then_downloads_the_same_task(self):
        for name, model in VERSIONS.items():
            for operation in ("generate", "edit"):
                with self.subTest(skill=name, operation=operation), tempfile.TemporaryDirectory() as temporary:
                    script = ROOT / name / "scripts/generate_image.py"
                    spec = importlib.util.spec_from_file_location(name + operation, script)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    reference = Path(temporary) / "reference.png"
                    reference.write_bytes(PNG)
                    with FakeAPI([
                        (202, {"task_id": "same-task", "status": "pending"}),
                        (200, {"task_id": "same-task", "status": "submitted"}),
                        (200, lambda base: {"task_id": "same-task", "status": "completed", "result_url": base + "/result.png"}),
                        (200, PNG),
                    ]) as api:
                        arguments = [operation, "--prompt", "A ceramic cup", "--async", "--wait",
                                     "--poll-interval", "0", "--base-url", api.base_url,
                                     "--download-dir", str(Path(temporary) / "images"), "--json"]
                        if operation == "edit":
                            arguments.extend(["--image-file", str(reference)])
                        output = io.StringIO()
                        with patch.dict(os.environ, {"OPENAI_API_KEY": "standalone-test-key"}, clear=True), contextlib.redirect_stdout(output):
                            code = module.main(arguments)
                    result = json.loads(output.getvalue())
                    self.assertEqual(code, 0, result)
                    self.assertEqual(result["task_id"], "same-task")
                    self.assertEqual(result["model"], model)
                    self.assertEqual([entry[0] for entry in api.requests], ["POST", "GET", "GET", "GET"])
                    self.assertEqual(api.requests[0][2]["model"], model)
                    self.assertNotIn("size", api.requests[0][2])
                    if operation == "edit":
                        self.assertTrue(api.requests[0][2]["image_urls"][0].startswith("data:image/png;base64,"))
                    self.assertEqual(Path(result["downloads"][0]).read_bytes(), PNG)
                    self.assertNotIn("standalone-test-key", output.getvalue())


if __name__ == "__main__":
    unittest.main()
