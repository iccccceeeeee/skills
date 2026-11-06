"""Offline request and recovery regressions for the image CLI."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "generate_image.py"
spec = importlib.util.spec_from_file_location("generate_image", SCRIPT)
assert spec and spec.loader
image = importlib.util.module_from_spec(spec)
spec.loader.exec_module(image)


class FakeAPI:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def __enter__(self):
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                self.respond()

            def do_GET(self):
                self.respond()

            def respond(self):
                raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                owner.requests.append((self.command, self.path, json.loads(raw) if raw else None))
                code, payload = owner.responses.pop(0)
                if callable(payload):
                    payload = payload(owner.base_url)
                body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
                self.send_response(code)
                self.send_header("Content-Type", "image/png" if isinstance(payload, bytes) else "application/json")
                self.end_headers()
                self.wfile.write(body)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


class ImageCLITests(unittest.TestCase):
    def parse(self, *args):
        return image.build_parser().parse_args(["generate", "--prompt", "A ceramic cup", *args])

    def invoke(self, api, *args):
        output = io.StringIO()
        with patch.dict(os.environ, {"OPENAI_API_KEY": "offline-secret"}, clear=True):
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
                code = image.main([*args, "--base-url", api.base_url, "--json"])
        return code, json.loads(output.getvalue())

    def test_model_selection_resolution_and_quality_defaults(self):
        for model in ("gpt-image-2", "gpt-image-2.5-flare", "gpt-image-2.5-sunburst", "gpt-image-2.6-flare", "gpt-image-2.6-sunburst"):
            with self.subTest(model=model):
                resolution = "1k" if model.startswith("gpt-image-2.6-") else "4k"
                payload = image.build_payload(self.parse("--model", model, "--resolution", resolution), require_reference=False)
                self.assertEqual(payload["model"], model)
                self.assertEqual(payload["image_size"], resolution.upper())
                self.assertNotIn("size", payload)
                self.assertEqual(payload["quality"], "medium" if model == "gpt-image-2" else "auto")

    def test_image26_higher_resolutions_are_sent_as_image_size(self):
        for model in ("gpt-image-2.6-flare", "gpt-image-2.6-sunburst"):
            for resolution in ("2k", "4k"):
                with self.subTest(model=model, resolution=resolution):
                    args = self.parse("--model", model, "--resolution", resolution)
                    payload = image.build_payload(args, require_reference=False)
                    self.assertEqual(payload["model"], model)
                    self.assertEqual(payload["image_size"], resolution.upper())
                    self.assertNotIn("size", payload)

    def test_bare_and_ext_models_are_rejected(self):
        for model in ("gpt-image-2.6", "gpt-image-2.6-ext"):
            with self.subTest(model=model), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    self.parse("--model", model)

    def test_new_models_reject_multiple_images_before_submission(self):
        for model in ("gpt-image-2.5-flare", "gpt-image-2.6-flare", "gpt-image-2.6-sunburst"):
            with self.subTest(model=model), self.assertRaises(image.UserError):
                image.build_payload(self.parse("--model", model, "--n", "2"), require_reference=False)
        payload = image.build_payload(self.parse("--n", "2"), require_reference=False)
        self.assertEqual(payload["n"], 2)

    def test_platform_reference_limit_is_eight(self):
        args = self.parse(*sum((["--image-url", f"https://example.test/{i}.png"] for i in range(8)), []))
        self.assertEqual(len(image.build_payload(args, require_reference=False)["image_urls"]), 8)
        args.image_url.append("https://example.test/9.png")
        with self.assertRaises(image.UserError):
            image.build_payload(args, require_reference=False)

    def test_model_specific_aspect_ratio_is_sent_without_size(self):
        payload = image.build_payload(self.parse("--model", "gpt-image-2.6-flare", "--aspect-ratio", "4:3"), require_reference=False)
        self.assertEqual(payload["aspect_ratio"], "4:3")
        self.assertNotIn("size", payload)
        with self.assertRaises(image.UserError):
            image.build_payload(self.parse("--model", "gpt-image-2.6-flare", "--aspect-ratio", "21:9"), require_reference=False)
        payload = image.build_payload(self.parse("--model", "gpt-image-2.5-flare", "--aspect-ratio", "21:9"), require_reference=False)
        self.assertEqual(payload["aspect_ratio"], "21:9")

    def test_sync_default_is_explicit(self):
        with FakeAPI([(200, {"data": [{"url": "https://example.test/a.png"}]})]) as api:
            code, result = self.invoke(api, "generate", "--prompt", "A cup")
        self.assertEqual(code, 0)
        self.assertEqual(api.requests[0][1], "/v1/images/generations?sync=1")
        self.assertEqual(result["model"], "gpt-image-2")
        self.assertEqual(result["urls"], ["https://example.test/a.png"])

    def test_unexpected_202_in_sync_mode_polls_the_same_task(self):
        with FakeAPI([(202, {"status": "pending", "task_id": "task-one"}), (200, {"status": "completed", "result_url": "https://example.test/a.png"})]) as api:
            code, result = self.invoke(api, "generate", "--prompt", "A cup", "--model", "gpt-image-2.6-flare")
        self.assertEqual(code, 0)
        self.assertEqual(result["task_id"], "task-one")
        self.assertEqual([r[0] for r in api.requests], ["POST", "GET"])
        self.assertEqual(api.requests[1][1], "/v1/images/tasks/task-one")

    def test_async_wait_polls_through_submitted_to_completion(self):
        responses = [
            (202, {"status": "pending", "task_id": "task-one"}),
            (200, {"status": "pending"}),
            (200, {"status": "submitted"}),
            (200, {"status": "completed", "result_url": "https://example.test/a.png"}),
        ]
        with FakeAPI(responses) as api:
            code, result = self.invoke(api, "generate", "--prompt", "A cup", "--async", "--wait", "--poll-interval", "0.001")
        self.assertEqual(code, 0)
        self.assertEqual(result["task_id"], "task-one")
        self.assertEqual(result["urls"], ["https://example.test/a.png"])
        self.assertEqual([request[0] for request in api.requests], ["POST", "GET", "GET", "GET"])
        self.assertEqual([request[1] for request in api.requests[1:]], ["/v1/images/tasks/task-one"] * 3)

    def test_async_submit_stays_submit_only(self):
        with FakeAPI([(202, {"status": "pending", "task_id": "task-one"})]) as api:
            code, result = self.invoke(api, "generate", "--prompt", "A cup", "--async")
        self.assertEqual(code, 0)
        self.assertEqual(len(api.requests), 1)
        self.assertEqual(api.requests[0][1], "/v1/images/generations?async=1")
        self.assertEqual(result["task_id"], "task-one")

    def test_poll_failure_preserves_task_and_redacts_key(self):
        with FakeAPI([(202, {"status": "pending", "task_id": "task-one"}), (503, {"error": {"message": "temporary offline-secret"}})]) as api:
            code, result = self.invoke(api, "generate", "--prompt", "A cup", "--async", "--wait")
        self.assertEqual(code, 1)
        self.assertEqual(result["task_id"], "task-one")
        self.assertEqual(result["stage"], "poll")
        self.assertNotIn("offline-secret", json.dumps(result))
        self.assertEqual([r[0] for r in api.requests], ["POST", "GET"])

    def test_download_failure_preserves_completed_result_and_task(self):
        response = lambda base: {"status": "completed", "result_url": base + "/image.png"}
        with FakeAPI([(200, response), (503, {"error": "temporary"})]) as api:
            import tempfile
            with tempfile.TemporaryDirectory() as directory:
                code, result = self.invoke(api, "poll", "task-one", "--wait", "--download-dir", directory)
        self.assertEqual(code, 1)
        self.assertEqual(result["stage"], "download")
        self.assertEqual(result["task_id"], "task-one")
        self.assertEqual(len(result["urls"]), 1)
        self.assertEqual([r[0] for r in api.requests], ["GET", "GET"])

    def test_version_copy_default_does_not_change_model_validation(self):
        with patch.object(image, "MODEL", "gpt-image-2.6-flare"):
            payload = image.build_payload(self.parse(), require_reference=False)
            self.assertEqual(payload["model"], "gpt-image-2.6-flare")
            self.assertEqual(payload["quality"], "auto")
            with self.assertRaises(image.UserError):
                image.build_payload(self.parse("--n", "2"), require_reference=False)

    def test_download_directory_failure_keeps_task_recoverable(self):
        import tempfile
        with FakeAPI([(200, {"status": "completed", "result_url": "https://example.test/image.png"})]) as api:
            with tempfile.NamedTemporaryFile() as existing_file:
                code, result = self.invoke(api, "poll", "task-one", "--download-dir", existing_file.name)
        self.assertEqual(code, 1)
        self.assertEqual(result["task_id"], "task-one")
        self.assertEqual(result["stage"], "download")
        self.assertEqual(len(result["urls"]), 1)
        self.assertEqual(len(api.requests), 1)

    def test_poll_timeout_preserves_task_without_resubmitting(self):
        with FakeAPI([(202, {"status": "pending", "task_id": "task-one"}), (200, {"status": "pending"})]) as api:
            code, result = self.invoke(api, "generate", "--prompt", "A cup", "--async", "--wait", "--max-wait", "0")
        self.assertEqual(code, 1)
        self.assertEqual(result["task_id"], "task-one")
        self.assertEqual([r[0] for r in api.requests], ["POST", "GET"])

    def test_task_id_is_one_path_segment(self):
        self.assertTrue(image.task_url("https://example.test", "a/b?c").endswith("/a%2Fb%3Fc"))

    def test_dry_run_needs_no_key_and_sends_no_request(self):
        output = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), contextlib.redirect_stdout(output):
            code = image.main(["generate", "--prompt", "A cup", "--model", "gpt-image-2.6-flare", "--dry-run", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["payload"]["model"], "gpt-image-2.6-flare")


if __name__ == "__main__":
    unittest.main()
