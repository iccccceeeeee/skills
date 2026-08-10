"""HTTP, trust-boundary, idempotency, and output contracts."""

from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _video_common import (  # noqa: E402
    ProtocolError,
    UserError,
    emit_result,
    new_idempotency_key,
    normalize_base_url,
    request_json,
    validate_https_url,
    validate_idempotency_key,
    positive_float,
    positive_int,
)
from fake_video_api import FakeVideoAPI  # noqa: E402


class HttpTests(unittest.TestCase):
    def test_post_sends_bearer_json_and_caller_idempotency_key_unchanged(self) -> None:
        caller_key = "Caller-Key_ABC-123"
        with FakeVideoAPI() as server:
            status, response = request_json(
                "POST",
                f"{server.base_url}/v1/videos/generations",
                api_key="network-secret",
                payload={"model": "test", "prompt": "hello"},
                headers={"Idempotency-Key": caller_key},
                timeout=1,
            )

            recorded = server.requests[0]

        self.assertEqual(status, 202)
        self.assertTrue(response["id"].startswith("vid_"))
        self.assertEqual(recorded["headers"]["Authorization"], "Bearer network-secret")
        self.assertEqual(recorded["headers"]["Content-Type"], "application/json")
        self.assertEqual(recorded["headers"]["Idempotency-Key"], caller_key)
        self.assertEqual(json.loads(recorded["body"]), {"model": "test", "prompt": "hello"})

    def test_generated_idempotency_key_has_the_public_format(self) -> None:
        key = new_idempotency_key()
        self.assertRegex(key, r"^idem_[0-9a-f]{32}$")
        self.assertLessEqual(len(key), 128)

    def test_idempotency_key_over_128_characters_is_rejected(self) -> None:
        with self.assertRaisesRegex(UserError, "128"):
            validate_idempotency_key("x" * 129)

    def test_post_is_never_retried_after_disconnect_timeout_or_server_error(self) -> None:
        cases = (("/disconnect", 1), ("/timeout", 0.03), ("/502", 1), ("/503", 1))
        for path, timeout in cases:
            with self.subTest(path=path), FakeVideoAPI() as server:
                with self.assertRaises(ProtocolError):
                    request_json(
                        "POST",
                        server.base_url + path,
                        api_key="secret",
                        payload={"prompt": "one attempt"},
                        timeout=timeout,
                    )
                self.assertEqual(len(server.requests), 1)

    def test_structured_http_error_preserves_status_and_error_code(self) -> None:
        with FakeVideoAPI() as server:
            with self.assertRaises(ProtocolError) as caught:
                request_json(
                    "POST",
                    server.base_url + "/503",
                    payload={"prompt": "failure"},
                    timeout=1,
                )

        self.assertEqual(caught.exception.status, 503)
        self.assertEqual(caught.exception.error_code, "upstream_503")
        self.assertIn("HTTP 503", str(caught.exception))

    def test_non_json_http_error_is_normalized(self) -> None:
        with FakeVideoAPI() as server:
            with self.assertRaises(ProtocolError) as caught:
                request_json(
                    "POST",
                    server.base_url + "/non-json-error",
                    payload={"prompt": "failure"},
                    timeout=1,
                )

        self.assertEqual(caught.exception.status, 500)
        self.assertIn("upstream exploded", str(caught.exception))

    def test_json_mode_writes_one_valid_document_to_stdout_only(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        result = {"ok": True, "idempotency_key": "idem_0123456789abcdef0123456789abcdef"}

        with redirect_stdout(stdout), redirect_stderr(stderr):
            emit_result(result, json_mode=True)

        self.assertEqual(json.loads(stdout.getvalue()), result)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(stdout.getvalue().count("\n"), 1)

    def test_human_mode_writes_progress_to_stderr_not_stdout(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            emit_result({"ok": True, "summary": "task accepted"}, json_mode=False)

        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "task accepted\n")

    def test_all_three_official_https_hosts_are_accepted_exactly(self) -> None:
        for host in ("api.icodeeasy.cc", "jp.icodeeasy.cc", "sg.icodeeasy.cc"):
            with self.subTest(host=host):
                self.assertEqual(normalize_base_url(f"https://{host}/"), f"https://{host}")

    def test_lookalike_and_wildcard_hosts_are_not_implicitly_trusted(self) -> None:
        hosts = (
            "api.icodeeasy.cc.example.com",
            "evil-api.icodeeasy.cc",
            "icodeeasy.cc",
            "x.jp.icodeeasy.cc",
        )
        for host in hosts:
            with self.subTest(host=host):
                with self.assertRaisesRegex(UserError, "trust-custom-base-url"):
                    normalize_base_url(f"https://{host}")

    def test_custom_https_host_requires_explicit_trust(self) -> None:
        with self.assertRaisesRegex(UserError, "trust-custom-base-url"):
            normalize_base_url("https://video-api.example")
        self.assertEqual(
            normalize_base_url("https://video-api.example/", trust_custom=True),
            "https://video-api.example",
        )

    def test_http_requires_loopback_and_both_explicit_gates(self) -> None:
        with self.assertRaises(UserError):
            normalize_base_url("http://127.0.0.1:8123", trust_custom=True)
        with self.assertRaises(UserError):
            normalize_base_url(
                "http://127.0.0.1:8123", allow_insecure_localhost=True
            )
        with self.assertRaises(UserError):
            normalize_base_url(
                "http://192.0.2.10:8123",
                trust_custom=True,
                allow_insecure_localhost=True,
            )
        self.assertEqual(
            normalize_base_url(
                "http://127.0.0.1:8123/",
                trust_custom=True,
                allow_insecure_localhost=True,
            ),
            "http://127.0.0.1:8123",
        )

    def test_base_url_rejects_userinfo_query_and_fragment(self) -> None:
        invalid = (
            "https://user@api.icodeeasy.cc",
            "https://api.icodeeasy.cc?token=secret",
            "https://api.icodeeasy.cc/#fragment",
        )
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(UserError):
                normalize_base_url(value)

    def test_recovery_reuses_original_task_and_conflicting_payload_creates_none(self) -> None:
        key = "recovery-key"
        first_payload = {"model": "test", "prompt": "same", "duration": 4}
        reordered_payload = {"duration": 4, "prompt": "same", "model": "test"}
        with FakeVideoAPI() as server:
            with self.assertRaises(ProtocolError):
                request_json(
                    "POST",
                    server.base_url + "/v1/videos/generations?disconnect=1",
                    payload=first_payload,
                    headers={"Idempotency-Key": key},
                    timeout=1,
                )
            original_task_id = server.tasks[key][1]
            self.assertEqual(len(server.requests), 1)

            status, recovered = request_json(
                "POST",
                server.base_url + "/v1/videos/generations",
                payload=reordered_payload,
                headers={"Idempotency-Key": key},
                timeout=1,
            )
            self.assertEqual((status, recovered["id"]), (202, original_task_id))

            with self.assertRaises(ProtocolError) as conflict:
                request_json(
                    "POST",
                    server.base_url + "/v1/videos/generations",
                    payload={"model": "test", "prompt": "changed", "duration": 4},
                    headers={"Idempotency-Key": key},
                    timeout=1,
                )

            self.assertEqual(conflict.exception.status, 409)
            self.assertEqual(conflict.exception.error_code, "idempotency_conflict")
            self.assertEqual(server.created_task_count, 1)
            self.assertEqual(len(server.requests), 3)

    def test_generic_cli_validators_reject_non_positive_or_non_https_values(self) -> None:
        self.assertEqual(positive_int("2"), 2)
        self.assertEqual(positive_float("0.5"), 0.5)
        self.assertEqual(validate_https_url("https://media.example/video.mp4"),
                         "https://media.example/video.mp4")
        for validator, value in (
            (positive_int, "0"),
            (positive_float, "-0.1"),
            (validate_https_url, "http://media.example/video.mp4"),
            (validate_https_url, "data:video/mp4;base64,AAAA"),
        ):
            with self.subTest(validator=validator.__name__, value=value):
                with self.assertRaises(Exception):
                    validator(value)

    def test_positive_float_rejects_non_finite_numbers(self) -> None:
        for value in ("nan", "inf", "-inf"):
            with self.subTest(value=value), self.assertRaises(Exception):
                positive_float(value)


if __name__ == "__main__":
    unittest.main()
