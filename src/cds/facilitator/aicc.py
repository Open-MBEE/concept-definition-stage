"""The AICC loop (T4) — Ask → Ingest → Confirm → Conform, mechanically constrained.

The model proposes tool calls; this loop is the boundary that makes the constraints real:

* **K1** — only registry tools execute; anything else is refused in-band and audited.
* **K2** — ``cds_commit`` is withheld from the model entirely (committing is human).
* **K5 / LLM.1** — the *mandated dead-end*: once the model files a retrieval item
  (``cds_queue_add``, the unsecured-canon escalation), every subsequent WRITE tool call in
  the same turn is refused. Escalate-then-stop is enforced, not requested.

The model's output is treated as untrusted (spec §12): every call passes the same Pydantic
gates, SHACL checks, and audit trail as any other caller.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cds.core.workspace import Project
from cds.facilitator import prompts
from cds.facilitator.decode import LLMBackend, ToolCall
from cds.mcp import tools as mcp_tools
from cds.mcp.tools import ToolMode


@dataclass(frozen=True)
class ExecutedCall:
    name: str
    arguments: dict[str, Any]
    result: str


@dataclass(frozen=True)
class RefusedCall:
    name: str
    reason: str


@dataclass
class TurnResult:
    reply: str = ""
    executed: list[ExecutedCall] = field(default_factory=list)
    refused: list[RefusedCall] = field(default_factory=list)
    escalated: bool = False  # the queue dead-end fired this turn


def _summarize(result: object) -> str:
    text = repr(result)
    return text if len(text) <= 2000 else text[:2000] + "…"


def _execute(call: ToolCall, project: Project, state: TurnResult) -> str:
    """Run one requested call through the guards; returns the in-band tool message."""
    if call.name not in prompts.offered_tool_names():
        reason = (f"tool {call.name!r} is not available — the complete tool list is in "
                  "your instructions; nothing outside it exists")
        state.refused.append(RefusedCall(name=call.name, reason=reason))
        return reason
    spec = mcp_tools.TOOLS[call.name]
    if state.escalated and spec.mode is not ToolMode.READ:
        reason = ("refused: unsecured canon was escalated to the retrieval queue this "
                  "turn — authoring stops here until a human secures the source "
                  "(the mandated dead-end)")
        state.refused.append(RefusedCall(name=call.name, reason=reason))
        return reason
    try:
        result = spec.fn(project, **call.arguments)
    except Exception as exc:
        reason = f"{type(exc).__name__}: {exc}"
        state.refused.append(RefusedCall(name=call.name, reason=reason))
        return reason
    state.executed.append(ExecutedCall(name=call.name, arguments=dict(call.arguments),
                                       result=_summarize(result)))
    if call.name == "cds_queue_add":
        state.escalated = True
    return _summarize(result)


def run_turn(
    user_message: str,
    *,
    project: Project | None = None,
    backend: LLMBackend | None = None,
    history: list[dict[str, Any]] | None = None,
    max_rounds: int = 8,
) -> TurnResult:
    """One facilitation turn: the model plans tool calls, the loop executes the legal ones,
    results feed back, until the model answers in text (or the round budget ends)."""
    if project is None or backend is None:
        raise NotImplementedError(
            "the facilitator needs a session project and an LLM backend — configure the "
            "ADR-8 triplet (CDS_LLM_BASE_URL / CDS_LLM_MODEL / CDS_LLM_API_KEY)"
        )
    system = prompts.system_prompt()
    tools_schema = prompts.offered_tools_schema()
    messages: list[dict[str, Any]] = list(history or [])
    messages.append({"role": "user", "content": user_message})
    state = TurnResult()

    for _round in range(max_rounds):
        turn = backend.complete(system=system, messages=messages, tools=tools_schema)
        if not turn.tool_calls:
            state.reply = turn.text
            break
        messages.append({
            "role": "assistant", "content": turn.text or "",
            "tool_calls": [{"name": c.name, "arguments": c.arguments}
                           for c in turn.tool_calls],
        })
        for call in turn.tool_calls:
            outcome = _execute(call, project, state)
            messages.append({"role": "tool", "name": call.name, "content": outcome})
    else:
        state.reply = state.reply or "(round budget exhausted — summarizing is on you)"
    return state
