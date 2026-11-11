"""Offline regressions for the Seedream and FLUX request contracts."""
import contextlib
import io
import json
import unittest
from unittest.mock import patch

from test_generate_image import image


class SeedreamFluxTests(unittest.TestCase):
    def invoke(self, model, *args, command="generate", dry_run=True):
        output = io.StringIO()
        flags = ["--dry-run"] if dry_run else []
        with patch.object(image, "request_json") as request, patch.object(image, "resolve_api_key") as key:
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
                code = image.main([command, "--model", model, "--prompt", "测试", *args, *flags, "--json"])
            request.assert_not_called()
            key.assert_not_called()
        return code, json.loads(output.getvalue())

    def test_seedream_default_tiers_and_reference_request(self):
        models = {
            "seedream-5-5": "2K",
            "seedream-5-0-flash": "1K",
            "seedream-5-0-pro": "1K",
            "seedream-4-5": "2K",
            "seedream-4-0": "2K",
            "doubao-seedream-5-0-lite": "2K",
        }
        for model, tier in models.items():
            with self.subTest(model=model):
                code, result = self.invoke(model, "--async", "--image-url", "data:image/png;base64,YQ==")
                self.assertEqual(code, 0, result)
                self.assertTrue(result["url"].endswith("/v1/images/generations?async=1"))
                self.assertEqual(result["payload"], {
                    "model": model, "prompt": "测试", "n": 1,
                    "image_size": tier, "aspect_ratio": "1:1", "image_input": ["<data-url>"],
                })

    def test_flux_2_uses_pixel_size_and_accepts_zero_seed(self):
        for model in ("flux-2-pro", "flux-2-max", "flux-2-flex"):
            with self.subTest(model=model):
                code, result = self.invoke(model, "--size", "1920x1080", "--seed", "0")
                self.assertEqual(code, 0, result)
                self.assertEqual(result["payload"], {
                    "model": model, "prompt": "测试", "n": 1, "size": "1920x1080", "seed": 0,
                })

    def test_flux_3_uses_resolution_and_ratio_with_klein_seed(self):
        code, result = self.invoke("flux-3-image-klein", "--resolution", "768sq", "--aspect-ratio", "16:9", "--seed", "4294967295")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["payload"], {
            "model": "flux-3-image-klein", "prompt": "测试", "n": 1,
            "image_size": "768sq", "aspect_ratio": "16:9", "seed": 4294967295,
        })
        code, result = self.invoke("flux-3-image")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["payload"]["image_size"], "1K")
        self.assertEqual(result["payload"]["aspect_ratio"], "1:1")

    def test_only_seedream_55_allows_ten_references(self):
        references = [arg for i in range(10) for arg in ("--image-url", f"https://example.test/{i}.png")]
        code, result = self.invoke("seedream-5-5", *references)
        self.assertEqual(code, 0, result)
        self.assertEqual(len(result["payload"]["image_input"]), 10)
        for model, args, count in (
            ("seedream-5-5", references + references[:2], 10),
            ("seedream-5-0-pro", references, 8),
            ("flux-3-image", references, 8),
        ):
            with self.subTest(model=model, count=count):
                code, result = self.invoke(model, *args, dry_run=False)
                self.assertEqual(code, 1, result)
                self.assertIn(f"at most {count}", result["summary"])

    def test_incompatible_parameters_fail_before_credentials_and_submission(self):
        cases = (
            ("seedream-4-5", "generate", ("--resolution", "1.5k"), "resolution"),
            ("seedream-4-0", "generate", ("--prompt", "字" * 1001), "1000"),
            ("seedream-5-0-flash", "generate", ("--aspect-ratio", "9:21"), "aspect ratio"),
            ("seedream-5-5", "edit", ("--image-url", "https://example.test/a.png"), "generate"),
            ("flux-3-image", "edit", (), "generate"),
            ("flux-2-pro", "generate", ("--resolution", "2k"), "--size"),
            ("flux-2-max", "generate", ("--size", "4096x4096"), "4"),
            ("flux-2-flex", "generate", ("--size", "63x64"), "64"),
            ("flux-3-image", "generate", ("--size", "1024x1024"), "--size"),
            ("flux-3-image", "generate", ("--aspect-ratio", "auto"), "aspect ratio"),
            ("flux-3-image", "generate", ("--seed", "0"), "--seed"),
            ("flux-3-image-klein", "generate", ("--seed", "4294967296"), "4294967295"),
            ("flux-3-image-klein", "generate", ("--n", "2"), "one image"),
            ("flux-3-image-klein", "generate", ("--quality", "high"), "--quality"),
        )
        for model, command, args, error in cases:
            with self.subTest(model=model, command=command, args=args):
                code, result = self.invoke(model, *args, command=command, dry_run=False)
                self.assertEqual(code, 1, result)
                self.assertIn(error, result["summary"])
