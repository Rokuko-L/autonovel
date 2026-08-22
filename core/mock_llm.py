#!/usr/bin/env python3
"""
mock_llm.py -- Offline mock for the LLM API layer.

Every LLM call in autonovel flows through llm.call_llm(). Scripts bind
it at import time ("from llm import call_llm"), so installing the
mock rebinds EVERY module in sys.modules that still holds the original
reference. Install before or after importing pipeline modules -- both work.

Usage:

    from mock_llm import MockLLM

    mock = MockLLM()
    mock.add('{"overall_score": 8.0}')                  # matched in order
    mock.add('{"winner": "A"}', match="Compare these")  # only for prompts containing 'match'

    with mock.install():
        import evaluate  # safe: no network, scripted responses
        result = evaluate.call_judge_json(prompt, model=validation.ScoreOutput)

    assert mock.calls[0]["prompt"][:80] == ...

Responses are returned verbatim (they may be damaged/truncated JSON --
parse_json_response is expected to heal them, exactly like production).
An unexpected call (no unconsumed rule matches) raises AssertionError so
tests fail loudly instead of silently hitting the network.
"""

import sys
from pathlib import Path


class MockLLM:
    """Scripted replacement for llm.call_llm."""

    def __init__(self):
        self.rules = []   # [{"response": str, "match": str|None, "used": bool}]
        self.calls = []   # [{"prompt", "system", "kwargs"}]

    def add(self, response: str, match: str | None = None) -> "MockLLM":
        """Queue a response. With `match`, only prompts containing that
        substring consume this rule; otherwise rules are consumed in order."""
        self.rules.append({"response": response, "match": match, "used": False})
        return self

    def add_json(self, data, match: str | None = None) -> "MockLLM":
        """Queue a dict/list as a compact JSON response."""
        import json
        return self.add(json.dumps(data), match=match)

    # --- call_llm-compatible interface ---

    def __call__(self, prompt, system=None, **kwargs):
        self.calls.append({"prompt": prompt, "system": system, "kwargs": kwargs})
        for rule in self.rules:
            if rule["used"]:
                continue
            if rule["match"] is not None and rule["match"] not in prompt:
                continue
            rule["used"] = True
            return rule["response"]
        raise AssertionError(
            f"Unexpected LLM call #{len(self.calls)} (no unconsumed mock rule "
            f"matches). Prompt starts with: {prompt[:120]!r}"
        )

    # --- installation ---

    def install(self):
        """Context manager: rebind call_llm everywhere it's referenced."""
        return _Patched(self)

    # --- introspection helpers ---

    @property
    def prompts(self):
        return [c["prompt"] for c in self.calls]

    def last_prompt(self) -> str:
        return self.calls[-1]["prompt"]


class _Patched:
    def __init__(self, mock: MockLLM):
        self.mock = mock
        self._patched_modules = []

    def __enter__(self):
        from core import llm
        original = llm.call_llm
        self._original = original
        llm.call_llm = self.mock
        # Rebind in every already-imported module that holds the original.
        self._patched_modules = [
            name for name, mod in sys.modules.items()
            if getattr(mod, "call_llm", None) is original
        ]
        for name in self._patched_modules:
            setattr(sys.modules[name], "call_llm", self.mock)
        return self.mock

    def __exit__(self, *exc):
        from core import llm
        llm.call_llm = self._original
        for name in self._patched_modules:
            setattr(sys.modules[name], "call_llm", self._original)
        return False


def load_fixture(mock: MockLLM, path) -> MockLLM:
    """Load queued responses from a JSON file: [{"match": str|null, "response": str}]."""
    import json
    for rule in json.loads(Path(path).read_text(encoding="utf-8")):
        mock.add(rule["response"], match=rule.get("match"))
    return mock
