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
SHARED_SCRIPTS = Path("icodeeasy-image-generations/scripts")
IMAGE_2_SCRIPT = Path("image2-icodeeasy/scripts/generate_image.py")
IMAGE_25_SCRIPT = SHARED_SCRIPTS / "generate_image25.py"
IMAGE_26_SCRIPT = SHARED_SCRIPTS / "generate_image26.py"
VERSIONS = {
    "image2-icodeeasy": ("gpt-image-2", IMAGE_2_SCRIPT),
    "image25-flare-icodeeasy": ("gpt-image-2.5-flare", IMAGE_25_SCRIPT),
    "image25-sunburst-icodeeasy": ("gpt-image-2.5-sunburst", IMAGE_25_SCRIPT),
    "image26-flare-icodeeasy": ("gpt-image-2.6-flare", IMAGE_26_SCRIPT),
    "image26-sunburst-icodeeasy": ("gpt-image-2.6-sunburst", IMAGE_26_SCRIPT),
}
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl6lAsAAAAASUVORK5CYII="
)


class StandaloneSkillTests(unittest.TestCase):
    def test_static_image26_rejects_animation_flags(self):
        script = ROOT / IMAGE_26_SCRIPT
        for options in (("--format", "gif"), ("--frame-count", "9"),
                        ("--frame-duration-ms", "200"), ("--frame-size", "512x512")):
            with self.subTest(options=options):
                result = subprocess.run([
                    sys.executable, str(script), "generate", "--prompt", "A lantern",
                    "--dry-run", "--json", *options,
                ], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)

    def test_static_image26_higher_resolutions_are_sent_as_image_size(self):
        script = ROOT / IMAGE_26_SCRIPT
        for model in ("gpt-image-2.6-flare", "gpt-image-2.6-sunburst"):
            for resolution in ("2k", "4k"):
                with self.subTest(model=model, resolution=resolution):
                    result = subprocess.run([
                        sys.executable, str(script), "generate", "--prompt", "A lantern",
                        "--model", model, "--resolution", resolution, "--dry-run", "--json",
                    ], capture_output=True, text=True, env={})
                    self.assertEqual(result.returncode, 0, result.stderr)
                    payload = json.loads(result.stdout)["payload"]
                    self.assertEqual(payload["model"], model)
                    self.assertEqual(payload["image_size"], resolution.upper())
                    self.assertEqual(payload["output_format"], "png")

    def test_static_image26_high_res_checks_known_reference_formats(self):
        with tempfile.TemporaryDirectory() as directory:
            bmp = Path(directory) / "reference.bmp"
            bmp.write_bytes(b"BM")
            for script_path in (IMAGE_26_SCRIPT, SHARED_SCRIPTS / "generate_image.py"):
                script = ROOT / script_path
                for resolution, options, supported in (
                    ("2k", ["--image-file", str(bmp)], False),
                    ("4k", ["--image-url", "data:image/gif;base64,R0lG"], False),
                    ("4k", ["--image-url", "data:image/webp;base64,UklG"], True),
                    ("1k", ["--image-file", str(bmp)], True),
                ):
                    with self.subTest(script=script_path, resolution=resolution, options=options):
                        result = subprocess.run([
                            sys.executable, str(script), "edit", "--prompt", "A lantern",
                            "--model", "gpt-image-2.6-sunburst", "--resolution", resolution,
                            "--dry-run", "--json", *options,
                        ], capture_output=True, text=True, env={})
                        self.assertEqual(result.returncode, 0 if supported else 1, result.stdout + result.stderr)
                        response = json.loads(result.stdout)
                        if supported:
                            self.assertEqual(response["payload"]["image_urls"], ["<data-url>"])
                        else:
                            self.assertIn("PNG, JPEG, or WebP", response["summary"])

    def test_image2_accepts_the_requested_landscape_ratio(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / IMAGE_2_SCRIPT),
             "generate", "--prompt", "A landscape coffee cup photograph",
             "--aspect-ratio", "16:9", "--dry-run", "--json"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["payload"]["aspect_ratio"], "16:9")

    def test_each_skill_runs_from_its_installed_entry_and_runner(self):
        for name, (model, script_path) in VERSIONS.items():
            with self.subTest(skill=name), tempfile.TemporaryDirectory() as temporary:
                installed = Path(temporary)
                destination = installed / name
                shutil.copytree(ROOT / name, destination)
                runner = installed / script_path
                model_args = []
                if script_path != IMAGE_2_SCRIPT:
                    skill = (destination / "SKILL.md").read_text(encoding="utf-8")
                    self.assertIn(f"(../{script_path.as_posix()})", skill)
                    self.assertIn(f"--model {model}", skill)
                    runner.parent.mkdir(parents=True)
                    shutil.copy2(ROOT / script_path, runner)
                    model_args = ["--model", model]
                result = subprocess.run(
                    [sys.executable, str(runner), "generate", "--prompt", "A ceramic cup",
                     "--dry-run", "--json", *model_args],
                    cwd=temporary, capture_output=True, text=True, check=True,
                    env={key: value for key, value in os.environ.items()
                         if key not in ("OPENAI_API_KEY", "ANTHROPIC_AUTH_TOKEN", "PYTHONPATH")},
                )
                body = json.loads(result.stdout)
                self.assertEqual(body["payload"]["model"], model)
                self.assertEqual(body["payload"]["image_size"], "1K")
                self.assertEqual(body["payload"]["quality"], "medium" if model == "gpt-image-2" else "auto")

    def test_each_skill_generates_and_edits_then_downloads_the_same_task(self):
        for name, (model, script_path) in VERSIONS.items():
            for operation in ("generate", "edit"):
                with self.subTest(skill=name, operation=operation), tempfile.TemporaryDirectory() as temporary:
                    script = ROOT / script_path
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
                        if script_path != IMAGE_2_SCRIPT:
                            arguments.extend(["--model", model])
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
