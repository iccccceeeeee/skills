"""Authentication, prompt, and secret-handling contracts."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _video_common import (  # noqa: E402
    ProtocolError,
    UserError,
    load_prompt,
    request_json,
    resolve_api_key,
)
from fake_video_api import FakeVideoAPI  # noqa: E402


class AuthenticationTests(unittest.TestCase):
    def test_openai_key_has_priority_over_anthropic_token(self) -> None:
        environment = {
            "OPENAI_API_KEY": "openai-priority-key",
            "ANTHROPIC_AUTH_TOKEN": "anthropic-fallback-token",
        }
        with mock.patch.dict(os.environ, environment, clear=True):
            self.assertEqual(resolve_api_key(), ("openai-priority-key", "OPENAI_API_KEY"))

    def test_anthropic_token_is_the_fallback(self) -> None:
        with mock.patch.dict(
            os.environ, {"ANTHROPIC_AUTH_TOKEN": "anthropic-fallback-token"}, clear=True
        ):
            self.assertEqual(
                resolve_api_key(),
                ("anthropic-fallback-token", "ANTHROPIC_AUTH_TOKEN"),
            )

    def test_network_auth_resolution_fails_when_both_keys_are_missing(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(UserError, "OPENAI_API_KEY.*ANTHROPIC_AUTH_TOKEN"):
                resolve_api_key()

    def test_dry_run_can_resolve_without_any_api_key(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(resolve_api_key(required=False), ("", ""))

    def test_prompt_file_is_loaded_without_requiring_prompt_on_command_line(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            prompt_file = Path(directory) / "prompt.txt"
            prompt_file.write_text("  private cinematic prompt\n", encoding="utf-8")

            self.assertEqual(load_prompt(None, str(prompt_file)), "private cinematic prompt")

    def test_prompt_and_prompt_file_are_mutually_exclusive(self) -> None:
        with self.assertRaisesRegex(UserError, "either.*prompt.*prompt-file"):
            load_prompt("inline", "prompt.txt")

    def test_http_error_redacts_active_key_and_signed_url_query(self) -> None:
        api_key = "active-secret-value"
        with FakeVideoAPI() as server:
            with self.assertRaises(ProtocolError) as caught:
                request_json(
                    "POST",
                    f"{server.base_url}/secret-error",
                    api_key=api_key,
                    payload={"prompt": "safe"},
                    timeout=1,
                )

        message = str(caught.exception)
        self.assertNotIn(api_key, message)
        self.assertNotIn("signed-secret", message)
        self.assertIn("<redacted>", message)
        self.assertIn("https://media.example/video.mp4?<redacted>", message)

        response_text = repr(caught.exception.response)
        self.assertNotIn(api_key, response_text)
        self.assertNotIn("signed-secret", response_text)
        error = caught.exception.response["error"]
        self.assertIn("credential-<redacted>", error)
        self.assertIn("https://media.example/video.mp4?<redacted>", error)


if __name__ == "__main__":
    unittest.main()
