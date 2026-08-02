<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# LARP-mode agent user testing

> Owner requirement (2026-08-02): before any human user-tests an increment, LLM agents
> role-play real users **aggressively** against the running system, so what reaches the
> human is really ready — and design-intent drift is caught early and often.

## Protocol

1. **Public surfaces only.** The agent interacts exclusively through what a real user has:
   the HTTP APIs, the MCP endpoint, or (later) the web UI. It never reads source, tests, or
   internal docs — discovering the system cold *is the test*.
2. **In character, with a concrete persona.** A named user with a real project, real goals,
   zero prior cds knowledge unless the persona says otherwise. The session includes the
   happy path, realistic mistakes, frustration, and deliberate boundary probing.
3. **Drift check against design intent.** Every session verdicts the doctrine explicitly:
   candidates-only; commit-gate refusal (clear, non-scary); verification advisory +
   actionable (granular rule/focus/message); escalate-never-invent discoverable; the K1
   whitelist is the entire reachable surface; errors teach the construction order.
4. **Findings are issues.** Each finding gets a severity (blocker / major / minor /
   papercut), a repro, and "what the user expected"; findings land on the tracking issue
   (`Refs:`, never closing keywords) or as new issues when they're their own work.
5. **Early and often.** A LARP pass runs at every phase checkpoint (see cadence below) and
   after any change to a public surface. The playground ([docs/playground.md](../playground.md))
   is the fixture: if the LARP agent can't stand the system up from that page, that's
   finding #1.

## Cadence (per T8 phase)

| Phase | Session(s) | Personas / focus |
|---|---|---|
| **P1** ✅ | HTTP authoring session vs `cds-serve` + `cds-oracle` | cold-start engineer; discoverability, error quality, doctrine drift |
| P2 | staging → commit | a facilitator-user who *cannot* commit; a reviewer who can; held-out terms surfaced honestly |
| P3 | audit | an auditor replaying a session from provenance alone |
| P4 | conversation | a stakeholder talking to the AICC facilitator; **no-fabrication probes** (bait the agent with unsecured canon; it must queue, not invent) |
| P5/P6 | full web UAT | non-expert stakeholder in the Voilà app; hostile user probing for a code surface (K3) |

## Session report format

```
## Session log summary
## Findings   [F-n] severity | surface | what happened | expected | drift?
## Doctrine drift verdicts (one line per doctrine item)
## Top fixes before human user testing
```

## Related docs

[Playground](../playground.md) · [Testing methodology](methodology.md) ·
[Architecture spec](../architecture/cds-web-app.md)
