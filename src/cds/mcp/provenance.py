"""PROV-O stamping + verifiable append-only audit for LLM actions and commits (K4, P3).

Two instruments, both anchored on deterministic identities (no build-time clocks):

* :func:`stamp` — a PROV graph for one activity (a commit, keyed by its ChangePlan content
  hash): the activity, its associated agents (the human approver, optionally the mediating
  LLM as a ``prov:SoftwareAgent``, the session), and per-subject ``prov:wasGeneratedBy`` /
  ``prov:wasInvalidatedBy`` / ``prov:wasRevisionOf`` links.
* :class:`AuditLog` — hash-chained JSONL: every line carries the SHA-256 of the previous
  line, so append-only is *verifiable* (``verify_chain``), not asserted. Rewriting history
  breaks the chain; replay returns the events in order (REQ-K4.2).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rdflib import RDF, Graph, Literal, URIRef

from cds.core.namespaces import CDS, PROV


@dataclass(frozen=True)
class Attribution:
    """Who/what stands behind an activity: the accountable human, the session, and —
    when an LLM mediated — the model (attributed, never accountable)."""

    user: str
    session: str
    model: str | None = None
    version: str | None = None


def _model_agent_iri(model: str) -> URIRef:
    safe = "".join(c if c.isalnum() or c in "-._" else "-" for c in model)
    return URIRef(f"urn:cds:model:{safe}")


def stamp(
    triples: Iterable[URIRef],
    *,
    user: str,
    session: str,
    model: str | None = None,
    version: str | None = None,
    activity_iri: str | None = None,
) -> Graph:
    """A PROV graph attributing the given subjects to one activity.

    ``triples`` is the iterable of generated **subjects** (the K1 tools pass record IRIs).
    ``activity_iri`` should be deterministic (e.g. keyed on a ChangePlan content hash);
    when omitted, an activity is minted from the session id.
    """
    activity = URIRef(activity_iri) if activity_iri is not None \
        else URIRef(f"urn:cds:session:{session}:activity")
    g = Graph()
    g.add((activity, RDF.type, PROV.Activity))
    g.add((activity, CDS.sessionId, Literal(session)))
    # explicit negative assertion (auditor K-6): absence of a model is a claim, not a gap
    g.add((activity, CDS.llmMediated, Literal(model is not None)))
    if version is not None:
        g.add((activity, CDS.toolVersion, Literal(version)))
    user_iri = URIRef(user)
    g.add((user_iri, RDF.type, PROV.Agent))
    g.add((activity, PROV.wasAssociatedWith, user_iri))
    if model is not None:
        agent = _model_agent_iri(model)
        g.add((agent, RDF.type, PROV.SoftwareAgent))
        g.add((agent, CDS.modelId, Literal(model)))
        g.add((activity, PROV.wasAssociatedWith, agent))
        g.add((agent, PROV.actedOnBehalfOf, user_iri))  # the human stays accountable
    for subject in triples:
        g.add((subject, PROV.wasGeneratedBy, activity))
    return g


class AuditLog:
    """Hash-chained, append-only JSONL — rewriting any line breaks the chain."""

    _GENESIS = "0" * 64

    def __init__(self, path: Path) -> None:
        self.path = path

    @staticmethod
    def _digest(line: str) -> str:
        return hashlib.sha256(line.encode("utf-8")).hexdigest()

    def _lines(self) -> list[str]:
        if not self.path.exists():
            return []
        return [ln for ln in self.path.read_text(encoding="utf-8").splitlines() if ln]

    def append(self, event: dict[str, object]) -> None:
        from datetime import UTC, datetime

        lines = self._lines()
        prev = self._digest(lines[-1]) if lines else self._GENESIS
        # a wall-clock timestamp is a fact OF the event (auditor K-4) — the determinism
        # discipline governs the record build, not the event ledger
        record = {"seq": len(lines), "prev": prev,
                  "ts": datetime.now(UTC).isoformat(timespec="seconds"), "event": event}
        line = json.dumps(record, sort_keys=True)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:  # append mode ONLY
            fh.write(line + "\n")

    def replay(self) -> list[dict[str, Any]]:
        """The events, in order, as recorded."""
        return [json.loads(ln) for ln in self._lines()]

    def verify_chain(self) -> bool:
        """True iff every line's ``prev`` matches the digest of its predecessor."""
        prev = self._GENESIS
        for i, line in enumerate(self._lines()):
            record = json.loads(line)
            if record.get("seq") != i or record.get("prev") != prev:
                return False
            prev = self._digest(line)
        return True

    def entries(self) -> list[dict[str, Any]]:
        """The events with a per-row chain verdict (D2, live-QA 2026-08-02).

        Each entry: ``seq``, ``ts``, ``event`` (as recorded), and ``chain_ok`` — whether
        this line's ``seq``/``prev`` are consistent with everything before it. A doctored
        line breaks its successor's verdict (its recorded ``prev`` no longer matches).
        """
        out: list[dict[str, Any]] = []
        prev = self._GENESIS
        for i, line in enumerate(self._lines()):
            record = json.loads(line)
            ok = record.get("seq") == i and record.get("prev") == prev
            out.append({"seq": record.get("seq", i), "ts": record.get("ts", ""),
                        "event": record.get("event", {}), "chain_ok": ok})
            prev = self._digest(line)
        return out


def _ledger_rows(log: AuditLog) -> list[dict[str, str]]:
    seen_hashes: set[str] = set()
    rows: list[dict[str, str]] = []
    for entry in log.entries():
        event = entry["event"]
        action = str(event.get("action", "?"))
        if action == "commit":
            counts = (f"+{event.get('adds', 0)} ~{event.get('revisions', 0)} "
                      f"^{event.get('supersessions', 0)} -{event.get('retractions', 0)} "
                      f"held {event.get('held', 0)}")
            actor = str(event.get("approver", ""))
        else:
            counts = str(event.get("status", ""))
            actor = str(event.get("tool", ""))
        full_hash = str(event.get("content_hash", ""))
        note = ""
        if full_hash:
            if full_hash in seen_hashes:
                note = "repeat hash (no new changes)"
            seen_hashes.add(full_hash)
        if event.get("include_unverified"):
            joined = ", ".join(str(x) for x in event["include_unverified"])
            note = (note + "; " if note else "") + f"included unverified: {joined}"
        rows.append({
            "seq": str(entry["seq"]), "ts": str(entry["ts"]), "action": action,
            "actor": actor, "changes": counts, "hash": full_hash[:12],
            "chain": "ok" if entry["chain_ok"] else "BROKEN", "note": note,
        })
    return rows


_LEDGER_COLUMNS = ("seq", "ts", "action", "actor", "changes", "hash", "chain", "note")


def render_ledger(log: AuditLog, fmt: str = "md") -> str:
    """The audit trail as a scannable report (D2): a table with a per-row chain verdict
    under an overall banner. The hash chain stays the formal guarantee; this is the view
    a human can eyeball. ``fmt``: ``md`` (default) or ``csv``."""
    rows = _ledger_rows(log)
    if fmt == "csv":
        import csv
        import io

        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator="\n")
        writer.writerow(_LEDGER_COLUMNS)
        for row in rows:
            writer.writerow([row[c] for c in _LEDGER_COLUMNS])
        return buf.getvalue()
    if fmt != "md":
        raise ValueError(f"unknown ledger format {fmt!r}; expected md or csv")

    intact = log.verify_chain()
    banner = ("VERIFIED: chain intact" if intact
              else "WARNING: chain broken, this ledger has been altered")
    lines = [f"# Audit ledger ({banner})", ""]
    header = " | ".join(_LEDGER_COLUMNS)
    lines.append(f"| {header} |")
    lines.append("|" + "---|" * len(_LEDGER_COLUMNS))
    for row in rows:
        lines.append("| " + " | ".join(row[c] for c in _LEDGER_COLUMNS) + " |")
    lines.append("")
    lines.append(f"{len(rows)} event(s). Every row's chain cell is checked against the "
                 "hash of the previous line; verify independently with "
                 "AuditLog(path).verify_chain().")
    return "\n".join(lines) + "\n"
