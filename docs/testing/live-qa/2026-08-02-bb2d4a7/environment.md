# Environment & provenance — live-QA run 2026-08-02

This run **reflects exactly one commit**. If you re-run the same plan at a different commit, expect the
findings to differ — compare against [`findings.md`](findings.md), don't assume parity.

## Commit anchor

| Field | Value |
| --- | --- |
| Commit (full) | `bb2d4a7517862e205be49af5c00b2dc4418215c7` |
| Commit (short) | `bb2d4a7` |
| Branch | `feat/t8-concept-definition-app` |
| Commit date | `2026-08-02 16:53:23 -0400` |
| Commit subject | `feat(deploy): P6 tier — Traefik/Keycloak/JupyterHub composition, hardened per-user containers, hosting runbooks` |
| Working tree at run time | **CLEAN** (`git status --porcelain` empty) → QA reflects this commit with no local drift |

## Toolchain

| Tool | Version |
| --- | --- |
| OS | Darwin 25.5.0 (macOS, arm64) |
| Python | 3.12.12 (project `.venv`) |
| uv | 0.9.18 (Homebrew) |
| mcp SDK | **2.0.0** (relevant to finding B1 — the `func_metadata` `**fields` collapse) |
| Ollama model | **qwen2.5:7b** (Step 5 facilitator + eval) |
| Voilà kernel | `ipykernel` (had to be added — see B3) |

> Shell note: `VIRTUAL_ENV=/opt/anaconda3` was active, so every `uv` call printed a harmless
> "does not match the project environment path .venv" warning. uv used `.venv` regardless.

## Test baseline (Step 0)

```
uv sync --extra dev --extra mcp --extra oracle --extra facilitator
uv run pytest        # → 324 passed, 17 skipped in 7.90s
```

The 17 skips are creds/binary/ipywidgets-gated (`CDS_LLM_*`, `FLEXO_*`, typst, pdftotext, docker,
ipywidgets) and are environment-sensitive — a different host may show a different skip count with the
same pass set.

## Invocation pattern

Scratch projects were driven from outside the repo using the repo's `cds` binary:

```
uv run --project /Users/z/Documents/GitHub/cds cds <subcommand> …   # CLI, from /tmp/cds-play
uv run cds-serve  --canonical /tmp/cds-canon --role cds-reviewer --approver https://example.org/zargham --port 8800
uv run cds-oracle --port 8801
CDS_LLM_BASE_URL=http://localhost:11434/v1 CDS_LLM_MODEL=qwen2.5:7b CDS_LLM_API_KEY=ollama \
  uv run cds-serve --canonical /tmp/cds-canon --role cds-reviewer --port 8800   # Step 5
claude mcp add cds -- uv run --project /Users/z/Documents/GitHub/cds cds-mcp --canonical /tmp/cds-canon --role cds-reviewer
uv run --with voila,ipywidgets,ipykernel voila --port 8890 --no-browser src/cds/app/notebook/concept_definition_app.ipynb
```

## Expected findings at this commit (so a future run isn't surprised)

Confirmed bugs present at `bb2d4a7`: **B1** MCP link fields inert · **B2** no-op re-commit clobbers the
changeplan `.md` · **B3** Voilà Step-6 command missing `ipykernel` · **B4** facilitator silent
empty-turns (no temperature). If a later commit does **not** reproduce one of these, a fix landed —
record the fixing commit in [`decisions.md`](decisions.md). Full detail in [`findings.md`](findings.md).
