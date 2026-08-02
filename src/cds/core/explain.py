"""``cds explain`` — an in-CLI term lookup so a solo user isn't stranded on the vocabulary.

The cold-start test found every persona reaching for `cds explain`/`cds guide` and hitting "no such
command," with the canon shipped but unreachable without an AI or the PDF. This surfaces, for each
authorable kind: a **plain-language gloss** (ours), how to author it, and the **authoritative
citation**. It deliberately does *not* print the verbatim restricted canon text — consistent
with the view-layer discipline (cite, don't reproduce) — while still teaching the term.
"""

from __future__ import annotations

from functools import cache

from cds.core.model.instances import AUTHORABLE_KINDS, KIND_TERM

#: Plain-language, one-line glosses (our words, not the canon) for each authorable kind.
_GLOSS: dict[str, str] = {
    "mission": "The primary purpose of the effort — why it exists, in a line.",
    "goal": "A broad intended outcome. Goals are broad; objectives make them measurable.",
    "objective": "A specific, measurable version of a goal (link it with --refines <goal>).",
    "problem": "The pain or gap that motivates the effort.",
    "opportunity": "A favorable opening the effort seizes.",
    "driver": "An external force pushing the effort (a market, a mandate, a trend).",
    "constraint": "A hard boundary the solution must respect (budget, law, physics).",
    "moe": "A measure of effectiveness — how you'd know it's succeeding, operationally.",
    "stakeholder": "Anyone with a right, share, claim, or interest in the outcome.",
    "need": (
        "What a stakeholder needs, in *need-form* — 'the <stakeholder> needs the system to…', "
        "never 'shall' (requirements come in a later stage)."
    ),
    "position": (
        "A stakeholder's stance on another record — supports / opposes / prioritizes / "
        "constrains / reads-as. Divergent positions are valid and retained; verify surfaces "
        "them as a finding, never an error."
    ),
    # lifecycle verbs (ADR-9) — how records change without losing the durable record
    "retract": (
        "Retire a record with an append-only marker: it leaves the current view, but its "
        "content and the reason are preserved in the record forever."
    ),
    "supersede": (
        "Replace a record by authoring a NEW one with supersedes=<old-slug>: the old record "
        "is marked superseded (append-only) and leaves the current view; nothing is deleted."
    ),
    "discard": (
        "Delete a draft from the working copy (scratch mode) — safe before anything is "
        "committed; for committed records use retract instead."
    ),
}

#: How to author each kind (defaults to a generic template).
_USAGE: dict[str, str] = {
    "goal": "cds new goal <slug> --synthesis <s> [--addresses <problem>] --label … --description …",
    "objective": (
        "cds new objective <slug> --synthesis <s> --refines <goal> --label … --description …"
    ),
    "need": (
        "cds new need <slug> --synthesis <s> --for-stakeholder <st> --serves-goal <g> "
        "--label … --description …"
    ),
    "position": (
        "cds new position <slug> --synthesis <s> --characterizes <kind>/<slug> "
        "--held-by <stakeholder> --stance supports|opposes|prioritizes|constrains|reads-as "
        "--label … --description …"
    ),
    "retract": "cds retract <kind> <slug> --reason '…'   (HTTP/MCP: cds_retract)",
    "supersede": "cds new <kind> <new-slug> --supersedes <old-slug> …",
    "discard": "cds rm <kind> <slug>   (HTTP/MCP: cds_discard)",
}


@cache
def _term_index() -> dict[str, object]:
    from cds.stages.concept_definition.build import load_terms

    return {t.slug: t for t in load_terms()}


def _usage_for(kind: str) -> str:
    if kind in _USAGE:
        return _USAGE[kind]
    return f"cds new {kind} <slug> --synthesis <s> --label … --description …"


def explain(name: str) -> list[str] | None:
    """Display lines explaining a kind or term slug, or ``None`` if unknown."""
    slug = KIND_TERM.get(name, name)
    term = _term_index().get(slug)
    gloss = _GLOSS.get(name) or _GLOSS.get(slug)
    if term is None and gloss is None:
        return None

    label = getattr(term, "pref_label", None) or slug
    lines = [f"{label}  ({slug})", ""]
    if gloss:
        lines += [f"In plain terms: {gloss}", ""]
    if name in AUTHORABLE_KINDS or slug in KIND_TERM.values():
        kind = name if name in AUTHORABLE_KINDS \
            else next(k for k, v in KIND_TERM.items() if v == slug)
        lines += [f"Author it:  {_usage_for(kind)}", ""]
    elif name in _USAGE:  # lifecycle verbs
        lines += [f"How:  {_USAGE[name]}", ""]

    source = getattr(term, "definition_source", None) if term is not None else None
    grounding = getattr(term, "grounding", None) if term is not None else None
    if source:
        url = grounding[0].target if grounding else None
        lines.append(f"Authority:  {source}" + (f" — {url}" if url else ""))
        lines.append("(cds cites the authority; it does not reproduce restricted canon text.)")
    return lines


def glossary() -> list[str]:
    """A one-line-per-kind overview of the authorable vocabulary."""
    idx = _term_index()
    lines = ["Record kinds you can author:", ""]
    for kind in AUTHORABLE_KINDS:
        slug = KIND_TERM.get(kind, kind)
        label = getattr(idx.get(slug), "pref_label", None) or slug
        lines.append(f"  {kind:11s} {label} — {_GLOSS.get(kind, '')}")
    lines += ["", "Changing your mind: `cds explain retract | supersede | discard` (ADR-9).",
              "Run `cds explain <kind>` for detail on any one."]
    return lines
