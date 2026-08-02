"""The Voilà hardening configuration — K3's mechanical statement for the app tier.

Voilà renders the notebook server-side and, unlike Jupyter, exposes no cell-execution
surface to the browser by default; this module makes that posture EXPLICIT and testable
(REQ-K3.1), and is the single source the deploy tier reads when writing
``voila.json`` (P6). ``strip_sources`` removes even the read-only code listings;
``show_tracebacks=False`` keeps internals out of the page; ``allow_frontend_execute``
is our own guard flag — it must never become true.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def voila_settings() -> dict[str, Any]:
    """The hardened Voilà settings (the deploy tier serializes these to voila.json)."""
    return {
        "VoilaConfiguration": {
            "strip_sources": True,  # no code listings in the rendered page
            "show_tracebacks": False,  # no internals on error
            "allow_frontend_execute": False,  # guard flag: the browser never executes
        }
    }


def execute_disabled() -> bool:
    """True iff the app exposes no execute surface (REQ-K3.1's assertion)."""
    cfg = voila_settings()["VoilaConfiguration"]
    return bool(cfg["strip_sources"]) and not bool(cfg["allow_frontend_execute"])


def write_voila_json(directory: Path) -> Path:
    """Write ``voila.json`` for the app container (used by deploy/, P6)."""
    out = directory / "voila.json"
    out.write_text(json.dumps(voila_settings(), indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    return out
