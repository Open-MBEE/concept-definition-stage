"""Typst adapter: a ``SchemeView`` -> a deterministic Typst document -> PDF.

The Typst *source* is byte-deterministic (terms already sorted in the view); the PDF is produced by
the ``typst`` CLI. Typst is one View adapter over the projection — Markdown / OKF / MCP would be
others. Per the license-keyed discipline, the document embeds the verbatim definition only when the
View resolved it (``renders_restricted_canon``); otherwise it prints the citation instead.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from cds.core.render.view import SchemeView, TermView


def _escape(text: str) -> str:
    """Escape Typst markup characters in plain content."""
    out = text.replace("\\", "\\\\")
    for ch in ("#", "$", "*", "_", "`", "<", ">", "@", '"'):
        out = out.replace(ch, "\\" + ch)
    return out


def _term_block(term: TermView) -> str:
    lines = [f"=== {_escape(term.pref_label)}"]
    if term.alt_labels:
        lines.append(f"_aka {_escape(', '.join(term.alt_labels))}_")
    if term.definition is not None:
        lines.append(f"#quote(block: true)[{_escape(term.definition)}]")
        if term.definition_source is not None:
            lines.append(f"SEBoK attribution: {_escape(term.definition_source)}")
    elif term.citation is not None:
        # license-restricted: cite the authoritative source, do NOT reproduce the text
        lines.append(f'Definition withheld under the report license — see #link("{term.citation}")')
    if term.citation is not None:
        lines.append(f"Source: #link(\"{term.citation}\")")
    anchor = term.sysml_anchor if term.sysml_anchor is not None else "canon-only"
    lines.append(f"SysML anchor: {_escape(anchor)}")
    return "\n\n".join(lines)


def typst_document(view: SchemeView) -> str:
    """Render the View as deterministic Typst source."""
    canon_note = (
        "This report embeds verbatim SEBoK definitions; it therefore inherits SEBoK's text license "
        f"({view.text_license}, ShareAlike)."
        if view.renders_restricted_canon
        else "Definitions are restricted under the report's text license; this report cites the "
        "authoritative source instead of reproducing the text."
    )
    header = "\n".join(
        [
            "#set document(title: \"" + _escape(view.title) + "\")",
            "#set page(numbering: \"1\")",
            "#set heading(numbering: none)",
            "",
            f"= {_escape(view.title)}",
            "",
            f"Text license: {_escape(view.text_license)}. {_escape(canon_note)}",
            "",
        ]
    )
    return header + "\n\n" + "\n\n".join(_term_block(t) for t in view.terms) + "\n"


def render_pdf(view: SchemeView, out_pdf: Path) -> Path:
    """Compile the View to a PDF via the ``typst`` CLI; returns the PDF path."""
    source = typst_document(view)
    typ_path = out_pdf.with_suffix(".typ")
    typ_path.write_text(source)
    subprocess.run(["typst", "compile", str(typ_path), str(out_pdf)], check=True)
    return out_pdf
