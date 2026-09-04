#!/usr/bin/env python3
"""Wire-format tests for the multi-provider LLM client.

These drive call_llm() against httpx.MockTransport so the ASSERTIONS see
the exact HTTP request each provider dialect produces (URL path, auth
headers, payload keys) and the exact normalization of each response
shape — including TruncationError parity across dialects.

Run: uv run python -m unittest scratch.test_provider_llm
"""

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import llm


def _mock_client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


class ProviderResolutionTest(unittest.TestCase):
    def test_default_is_anthropic(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AUTONOVEL_PROVIDER", None)
            os.environ.pop("OPENAI_API_KEY", None)
            self.assertEqual(llm.resolve_provider("writer"), "anthropic")

    def test_global_override_applies_to_all_roles(self):
        with patch.dict(os.environ, {"AUTONOVEL_PROVIDER": "openai"}):
            for role in llm.ROLES:
                self.assertEqual(llm.resolve_provider(role), "openai")

    def test_role_override_beats_global(self):
        env = {"AUTONOVEL_PROVIDER": "openai", "AUTONOVEL_JUDGE_PROVIDER": "anthropic"}
        with patch.dict(os.environ, env):
            self.assertEqual(llm.resolve_provider("judge"), "anthropic")
            self.assertEqual(llm.resolve_provider("writer"), "openai")

    def test_key_inference_openai_only(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-x"}, clear=False):
            os.environ.pop("AUTONOVEL_PROVIDER", None)
            os.environ["ANTHROPIC_API_KEY"] = ""
            self.assertEqual(llm.resolve_provider("judge"), "openai")
            os.environ["ANTHROPIC_API_KEY"] = "sk-ant"
            self.assertEqual(llm.resolve_provider("judge"), "anthropic")

    def test_invalid_provider_raises_actionable_error(self):
        with patch.dict(os.environ, {"AUTONOVEL_PROVIDER": "mistral"}):
            with self.assertRaises(llm.ProviderError) as ctx:
                llm.resolve_provider("writer")
            self.assertIn("AUTONOVEL_PROVIDER", str(ctx.exception))

    def test_role_model_env_var_respected(self):
        with patch.dict(os.environ, {"AUTONOVEL_JUDGE_MODEL": "some/gateway-model"}):
            self.assertEqual(llm._resolve_model("anthropic", "judge"), "some/gateway-model")
        self.assertEqual(
            llm._resolve_model("openai", "judge"), llm.DEFAULT_MODELS["openai"]["judge"])


class AnthropicWireFormatTest(unittest.TestCase):
    """call_llm over the anthropic dialect must emit the same wire format as before."""

    def test_request_shape_and_auth(self):
        captured = {}
        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["headers"] = dict(request.headers)
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json={
                "content": [{"type": "text", "text": "ok"}],
                "stop_reason": "end_turn",
            })
        env = {
            "ANTHROPIC_API_KEY": "sk-ant-test",
            "ANTHROPIC_BASE_URL": "https://gateway.example",
        }
        for var in ("AUTONOVEL_PROVIDER", "AUTONOVEL_WRITER_PROVIDER"):
            env[var] = ""  # ensure absent
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("AUTONOVEL_PROVIDER", None)
            os.environ.pop("AUTONOVEL_WRITER_PROVIDER", None)
            original = llm.get_client()
            llm.set_client(_mock_client(handler))
            try:
                out = llm.call_llm("PROMPT", system="SYS", model_key="writer", beta_context=True)
            finally:
                llm.set_client(original)
        self.assertEqual(out, "ok")
        self.assertTrue(captured["url"].startswith("https://gateway.example/v1/messages"))
        self.assertEqual(captured["headers"]["x-api-key"], "sk-ant-test")
        self.assertEqual(captured["headers"]["anthropic-version"], "2023-06-01")
        self.assertEqual(captured["headers"]["anthropic-beta"], "context-1m-2025-08-07")
        self.assertEqual(captured["body"]["system"], "SYS")
        self.assertEqual(captured["body"]["messages"], [{"role": "user", "content": "PROMPT"}])
        self.assertIn("max_tokens", captured["body"])

    def test_no_key_header_when_keyless(self):
        captured = {}
        def handler(request: httpx.Request) -> httpx.Response:
            captured["headers"] = dict(request.headers)
            return httpx.Response(200, json={"content": [{"type": "text", "text": "x"}]})
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "", "ANTHROPIC_BASE_URL": "http://localhost:8787"}):
            os.environ.pop("AUTONOVEL_PROVIDER", None)
            original = llm.get_client()
            llm.set_client(_mock_client(handler))
            try:
                llm.call_llm("p", model_key="writer")
            finally:
                llm.set_client(original)
        self.assertNotIn("x-api-key", captured["headers"])


class OpenAIWireFormatTest(unittest.TestCase):
    def test_request_shape_system_message_and_bearer(self):
        captured = {}
        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["headers"] = dict(request.headers)
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json={
                "choices": [{"message": {"role": "assistant", "content": "hi"}, "finish_reason": "stop"}],
            })
        # gpt-4o (non-reasoning) exercises the max_tokens+temperature path;
        # the reasoning path has its own test below.
        env = {"OPENAI_API_KEY": "sk-oai", "OPENAI_BASE_URL": "https://openrouter.example/api/v1",
               "AUTONOVEL_WRITER_MODEL": "gpt-4o"}
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("AUTONOVEL_PROVIDER", None)
            os.environ.pop("AUTONOVEL_WRITER_PROVIDER", None)
            original = llm.get_client()
            llm.set_client(_mock_client(handler))
            try:
                out = llm.call_llm("PROMPT", system="SYS", model_key="writer")
            finally:
                llm.set_client(original)
        self.assertEqual(out, "hi")
        # base URL keeps its /v1 prefix; path appends chat/completions
        self.assertTrue(captured["url"].startswith("https://openrouter.example/api/v1/chat/completions"))
        self.assertEqual(captured["headers"]["authorization"], "Bearer sk-oai")
        self.assertNotIn("x-api-key", captured["headers"])
        roles = [m["role"] for m in captured["body"]["messages"]]
        self.assertEqual(roles, ["system", "user"])
        self.assertEqual(captured["body"]["messages"][0]["content"], "SYS")
        self.assertIn("max_tokens", captured["body"])
        self.assertIn("temperature", captured["body"])

    def test_reasoning_model_gets_max_completion_tokens_no_temperature(self):
        captured = {}
        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json={
                "choices": [{"message": {"content": "x"}, "finish_reason": "stop"}]})
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk", "AUTONOVEL_WRITER_MODEL": "gpt-5.2"}):
            os.environ.pop("AUTONOVEL_PROVIDER", None)
            original = llm.get_client()
            llm.set_client(_mock_client(handler))
            try:
                llm.call_llm("p", model_key="writer")
            finally:
                llm.set_client(original)
        self.assertIn("max_completion_tokens", captured["body"])
        self.assertNotIn("max_tokens", captured["body"])
        self.assertNotIn("temperature", captured["body"])

    def test_truncation_parity_finish_reason_length(self):
        """finish_reason 'length' must trip TruncationError exactly like stop_reason max_tokens."""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={
                "choices": [{"message": {"content": "partial"}, "finish_reason": "length"}]})
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk"}):
            os.environ.pop("AUTONOVEL_PROVIDER", None)
            original = llm.get_client()
            llm.set_client(_mock_client(handler))
            try:
                with self.assertRaises(llm.TruncationError):
                    llm.call_llm("p", model_key="writer")
            finally:
                llm.set_client(original)

    def test_sse_stream_body_parsed(self):
        """Gateways sometimes stream even when we didn't ask; chunks must parse."""
        sse = (
            'data: {"choices":[{"delta":{"content":"Hel"}}]}\n\n'
            'data: {"choices":[{"delta":{"content":"lo"}}]}\n\n'
            'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\n'
            "data: [DONE]\n\n"
        )
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text=sse, headers={"content-type": "text/event-stream"})
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk"}):
            os.environ.pop("AUTONOVEL_PROVIDER", None)
            original = llm.get_client()
            llm.set_client(_mock_client(handler))
            try:
                out = llm.call_llm("p", model_key="writer")
            finally:
                llm.set_client(original)
        self.assertEqual(out, "Hello")


class ExtraHeadersTest(unittest.TestCase):
    def test_extra_headers_merged_into_request(self):
        captured = {}
        def handler(request: httpx.Request) -> httpx.Response:
            captured["headers"] = dict(request.headers)
            return httpx.Response(200, json={"choices": [{"message": {"content": "x"}}]})
        env = {
            "OPENAI_API_KEY": "sk",
            "AUTONOVEL_EXTRA_HEADERS": json.dumps({"X-Title": "autonovel", "HTTP-Referer": "https://example.com"}),
        }
        with patch.dict(os.environ, env):
            os.environ.pop("AUTONOVEL_PROVIDER", None)
            original = llm.get_client()
            llm.set_client(_mock_client(handler))
            try:
                llm.call_llm("p", model_key="writer")
            finally:
                llm.set_client(original)
        self.assertEqual(captured["headers"]["x-title"], "autonovel")
        self.assertEqual(captured["headers"]["http-referer"], "https://example.com")

    def test_invalid_extra_headers_json_raises(self):
        with patch.dict(os.environ, {"AUTONOVEL_EXTRA_HEADERS": "{not json"}):
            with self.assertRaises(llm.ProviderError):
                llm._load_extra_headers()


if __name__ == "__main__":
    unittest.main()
