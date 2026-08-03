"""Shared user-facing text (U1, live-QA 2026-08-02 @ bb2d4a7).

One home for the strings a *user* of the services, CLI, or web app reads, so the same
plain-language wording is transcluded everywhere it appears instead of drifting per
surface. House rules, enforced by ``tests/unit/test_usertext.py``:

- write for an outside reader: no internal coordination labels (K1, K2,
  "correct-by-construction") and no operator flag names on end-user surfaces;
- no em-dashes in rendered text;
- refusals reassure (what is safe), then give the reader a next step they can act on.

The architecture docs keep the internal vocabulary; this module is the translation.
"""

from __future__ import annotations

# ---------------------------------------------------------------- service front doors

FACILITATOR_TITLE = "cds facilitator"
FACILITATOR_DESCRIPTION = (
    "Guided authoring for a concept-definition record. Each /tools endpoint checks its "
    "input, writes a draft into your session (never the shared record), and verification "
    "gives advisory feedback while you compose. Publishing a change to the shared record "
    "is a separate, human-approved commit step."
)

ORACLE_TITLE = "cds conformance oracle"
ORACLE_DESCRIPTION = (
    "Checks a model against the cds model family. Send a model instance to /verify and "
    "get a verdict plus itemized findings (each names the rule, the record it concerns, "
    "and what to do about it); /rules lists every rule the oracle applies. The oracle "
    "only checks; it never stores or changes anything."
)

MCP_SERVER_DESCRIPTION = (
    "cds tool server for MCP clients. Serves the fixed set of cds authoring and "
    "review tools; writes are drafts in the session until a reviewer commits them."
)

# ------------------------------------------------------------------------- refusals

COMMIT_NEEDS_REVIEWER = (
    "committing requires a reviewer: publishing to the durable record is a human "
    "decision. Your staged drafts are preserved. Ask someone with the cds-reviewer "
    "role to review and commit them."
)

COMMIT_SESSION_UNBOUND = (
    "this session is not connected to a durable record, so there is nothing to commit "
    "to. Your drafts remain safely in the session. Ask whoever runs this service to "
    "connect a record and grant a reviewer."
)

STAGED_COUNT_NOTE = (
    "Drafts live in your session only until a reviewer commits them; if the session "
    "ends first, they are gone. Compile or commit anything you want to keep."
)
