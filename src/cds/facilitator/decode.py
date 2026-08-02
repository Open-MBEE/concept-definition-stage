"""BYO-LLM backend seam (ADR-8) — the OpenAI-compatible triplet, and a scripted test double.

The operator configures exactly three values (``CDS_LLM_BASE_URL`` / ``CDS_LLM_MODEL`` /
``CDS_LLM_API_KEY``) — the de-facto universal surface covering hosted providers and
self-hosted stacks (Ollama, vLLM, llama.cpp, …). The client is stdlib HTTP: no SDK
dependency, no provider lock-in. Tests inject :class:`ScriptedBackend` behind the same
Protocol, so the AICC loop's guards are exercised deterministically without credentials.

(The ``anthropic``/``instructor`` extras remain available for a future native structured-
output path; the K-gates are identical either way — ADR-8.)
"""

from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class LLMConfig:
    """The ADR-8 endpoint triplet — operator configuration, never end-user UX.

    ``temperature`` defaults to 0: the tool-planning loop wants near-deterministic
    decoding (B4, live-QA 2026-08-02: an unset temperature left a local model at ~0.7
    and 3/5 turns came back empty). Operators may raise it via ``CDS_LLM_TEMPERATURE``.
    """

    base_url: str
    model: str
    api_key: str
    temperature: float = 0.0

    @classmethod
    def from_env(cls) -> LLMConfig | None:
        base = os.environ.get("CDS_LLM_BASE_URL")
        model = os.environ.get("CDS_LLM_MODEL")
        key = os.environ.get("CDS_LLM_API_KEY")
        if not (base and model and key):
            return None
        temperature = float(os.environ.get("CDS_LLM_TEMPERATURE", "0"))
        return cls(base_url=base.rstrip("/"), model=model, api_key=key,
                   temperature=temperature)


@dataclass(frozen=True)
class ToolCall:
    """One tool invocation the model requested."""

    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class AssistantTurn:
    """What the model produced: tool calls to run, and/or final text."""

    text: str = ""
    tool_calls: tuple[ToolCall, ...] = ()


class LLMBackend(Protocol):
    """The model seam: chat messages + offered tools in, an assistant turn out."""

    def complete(self, *, system: str, messages: list[dict[str, Any]],
                 tools: list[dict[str, Any]]) -> AssistantTurn: ...


@dataclass
class ScriptedBackend:
    """Deterministic test double: replays canned turns and records what it was shown."""

    turns: list[AssistantTurn]
    seen_messages: list[list[dict[str, Any]]] = field(default_factory=list)
    _cursor: int = 0

    def complete(self, *, system: str, messages: list[dict[str, Any]],
                 tools: list[dict[str, Any]]) -> AssistantTurn:
        self.seen_messages.append(list(messages))
        if self._cursor >= len(self.turns):
            return AssistantTurn(text="(script exhausted)")
        turn = self.turns[self._cursor]
        self._cursor += 1
        return turn


@dataclass(frozen=True)
class OpenAICompatBackend:
    """Chat-completions with function calling against any OpenAI-compatible endpoint."""

    config: LLMConfig
    timeout: float = 120.0

    def complete(self, *, system: str, messages: list[dict[str, Any]],
                 tools: list[dict[str, Any]]) -> AssistantTurn:
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": [{"role": "system", "content": system}, *messages],
            "temperature": self.config.temperature,
        }
        if tools:
            payload["tools"] = tools
        request = urllib.request.Request(
            f"{self.config.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
        message = body["choices"][0]["message"]
        calls: list[ToolCall] = []
        for tc in message.get("tool_calls") or []:
            fn = tc.get("function", {})
            try:
                arguments = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                arguments = {}
            calls.append(ToolCall(name=str(fn.get("name", "")), arguments=arguments))
        return AssistantTurn(text=str(message.get("content") or ""),
                             tool_calls=tuple(calls))
