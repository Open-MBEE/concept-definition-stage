"""P4 — the AICC facilitator: a constrained LLM over the K1 registry.

Everything here runs WITHOUT credentials via the ScriptedBackend seam: the loop's guards
are mechanical, so they are testable deterministically. K1: unknown tools are refused at
the boundary. K5/LLM.1: after `cds_queue_add` (unsecured canon), further WRITE tools that
turn are refused — the dead-end is enforced, not just prompted. K2: `cds_commit` is never
offered to the model.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from cds.core.authoring import project_graph
from cds.core.workspace import Project
from cds.facilitator import aicc, decode, prompts
from cds.mcp import staging


@pytest.fixture()
def session(tmp_path: Path) -> Project:
    return staging.new_session_project("https://cds.example/p4/", root=tmp_path / "s")


def _call(name: str, **args: object) -> decode.ToolCall:
    return decode.ToolCall(name=name, arguments=dict(args))


# --------------------------------------------------------------------- decode: the seam


def test_llm_config_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("CDS_LLM_BASE_URL", "CDS_LLM_MODEL", "CDS_LLM_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    assert decode.LLMConfig.from_env() is None
    monkeypatch.setenv("CDS_LLM_BASE_URL", "https://api.example/v1")
    monkeypatch.setenv("CDS_LLM_MODEL", "some-model")
    monkeypatch.setenv("CDS_LLM_API_KEY", "sk-test")
    cfg = decode.LLMConfig.from_env()
    assert cfg is not None and cfg.model == "some-model"


def test_scripted_backend_satisfies_protocol() -> None:
    backend: decode.LLMBackend = decode.ScriptedBackend([
        decode.AssistantTurn(tool_calls=(_call("cds_list", kind="goal"),)),
        decode.AssistantTurn(text="done"),
    ])
    turn = backend.complete(system="s", messages=[], tools=[])
    assert turn.tool_calls and turn.tool_calls[0].name == "cds_list"


# ------------------------------------------------------------------ prompts: the contract


def test_system_prompt_carries_the_deontic_manifest() -> None:
    text = prompts.system_prompt()
    for tool in ("cds_new", "cds_queue_add", "cds_retract"):
        assert tool in text
    assert "cds_commit" not in prompts.offered_tool_names()  # K2: committing is human
    assert "never" in text.lower() and "fabricat" in text.lower()  # the one inviolable rule
    assert prompts.system_prompt() == prompts.system_prompt()  # deterministic


# ------------------------------------------------------------------------ aicc: the loop


def test_turn_executes_whitelisted_tools(session: Project) -> None:
    backend = decode.ScriptedBackend([
        decode.AssistantTurn(tool_calls=(
            _call("cds_synthesis", slug="pilot", title="Pilot"),
            _call("cds_new", kind="goal", slug="g1", label="Goal",
                  description="A goal.", synthesis="pilot"),
        )),
        decode.AssistantTurn(text="Created the mapping and a first goal."),
    ])
    result = aicc.run_turn("set up a pilot mapping with one goal",
                           project=session, backend=backend)
    assert result.reply == "Created the mapping and a first goal."
    assert [c.name for c in result.executed] == ["cds_synthesis", "cds_new"]
    assert len(project_graph(session)) > 0


def test_unknown_tool_refused_and_reported(session: Project) -> None:
    backend = decode.ScriptedBackend([
        decode.AssistantTurn(tool_calls=(_call("run_python", code="import os"),)),
        decode.AssistantTurn(text="understood"),
    ])
    result = aicc.run_turn("try something sneaky", project=session, backend=backend)
    assert result.refused and result.refused[0].name == "run_python"
    assert not result.executed  # K1: nothing outside the whitelist ever runs
    # and the model was told, in-band, that the tool does not exist
    assert any("not available" in str(m) for m in backend.seen_messages[-1])


def test_unsecured_canon_escalates(session: Project) -> None:
    """LLM.1 / REQ-K5 — the mandated dead-end is MECHANICAL: after queuing unsecured
    canon, further write tools this turn are refused; the loop ends the authoring leg."""
    backend = decode.ScriptedBackend([
        decode.AssistantTurn(tool_calls=(
            _call("cds_synthesis", slug="pilot", title="Pilot"),
            _call("cds_queue_add", slug="sebok-need",
                  question="Secure the verbatim SEBoK definition of 'need'"),
            _call("cds_new", kind="goal", slug="sneak", label="Sneak",
                  description="Should be refused after the dead-end.", synthesis="pilot"),
        )),
        decode.AssistantTurn(text="Queued the retrieval; stopping here."),
    ])
    result = aicc.run_turn("add the official SEBoK definition of need",
                           project=session, backend=backend)
    assert result.escalated  # the dead-end fired
    executed = [c.name for c in result.executed]
    assert "cds_queue_add" in executed
    assert "cds_new" not in executed  # write AFTER the dead-end was refused
    assert any(c.name == "cds_new" for c in result.refused)
    g = project_graph(session)
    assert (None, None, None) in g  # queue item exists…
    assert "sneak" not in g.serialize(format="nt")  # …the sneaked write does not


def test_commit_is_never_offered_nor_executable(session: Project) -> None:
    backend = decode.ScriptedBackend([
        decode.AssistantTurn(tool_calls=(_call("cds_commit"),)),
        decode.AssistantTurn(text="ok"),
    ])
    result = aicc.run_turn("commit everything now", project=session, backend=backend)
    assert not result.executed
    assert result.refused and result.refused[0].name == "cds_commit"


def test_reads_still_allowed_after_escalation(session: Project) -> None:
    backend = decode.ScriptedBackend([
        decode.AssistantTurn(tool_calls=(
            _call("cds_queue_add", slug="q1", question="Secure canon X"),
            _call("cds_list", kind="goal"),
        )),
        decode.AssistantTurn(text="queued; here is the current state"),
    ])
    result = aicc.run_turn("…", project=session, backend=backend)
    assert [c.name for c in result.executed] == ["cds_queue_add", "cds_list"]


@pytest.mark.skipif(not os.environ.get("CDS_LLM_API_KEY"),
                    reason="live LLM smoke needs the ADR-8 triplet in the environment")
def test_live_llm_smoke(session: Project) -> None:  # pragma: no cover — creds-gated
    cfg = decode.LLMConfig.from_env()
    assert cfg is not None
    result = aicc.run_turn("Create a synthesis called 'smoke' titled 'Smoke test'.",
                           project=session, backend=decode.OpenAICompatBackend(cfg))
    assert result.reply
