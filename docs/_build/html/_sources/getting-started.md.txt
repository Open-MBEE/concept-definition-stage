# Getting started

This walks you from nothing to your first **concept-definition mapping** — a structured, checkable
record of your project's mission, goals, stakeholders, and needs, plus a readable brief.

You don't need any systems-engineering background. `cds` supplies the vocabulary (from SEBoK and
INCOSE) and checks your work; you supply the real-world knowledge about your project.

## 1. Install

Requires **Python 3.11+**. Install into an isolated virtual environment:

```bash
git clone https://github.com/Open-MBEE/concept-definition-stage
cd concept-definition-stage
python3.11 -m venv .venv && source .venv/bin/activate   # create & activate the env
pip install -e .
cds --version                                           # confirm it's installed
```

Prefer [`uv`](https://docs.astral.sh/uv/)? Install it first, then `uv venv && uv pip install -e .`.
(Once published to PyPI this all becomes a plain `pip install`.) See
[Troubleshooting](#troubleshooting) if a step fails.

## 2. Start a workspace in *your* project

`cds` writes your analysis into **your** repository — never into its own install. Make a folder for
your project and initialize it:

```bash
mkdir my-analysis && cd my-analysis
cds init --name my-analysis
```

This creates a `cds.toml` marker, a `concept-definition/` folder for your data and briefs, and — if
you use an AI-assisted editor — an assistant contract (`AGENTS.md`) and a facilitation skill so the
model in your editor can help you.

## 3. Two ways to work

**A. Guided by an AI assistant (recommended).** In an AI editor (e.g. Claude Code), ask it to
facilitate your concept definition. It follows the vendored skill: it interviews you one question at a
time, reflects your answers back in the proper vocabulary, and records them with the CLI for you. You
talk; it ledgers. This is the intended experience.

**B. By hand with the CLI.** You can drive every command yourself. The rest of this guide shows the
CLI directly so you understand what's happening underneath.

## 4. The building blocks

A mapping is a **synthesis** (the container) plus **records** typed by a small vocabulary:

| Kind | What it is |
| --- | --- |
| `mission` | the primary purpose of the effort |
| `goal` | a broad intended outcome |
| `objective` | a measurable version of a goal (`--refines <goal>`) |
| `problem` / `opportunity` | what motivates the effort |
| `driver` / `constraint` | external forces / hard boundaries |
| `moe` | a measure of effectiveness |
| `stakeholder` | anyone with a right, share, claim, or interest |
| `need` | a stakeholder need, in "need form" (never "shall") |

Not sure what a term means? **Look it up:** `cds explain <kind>` prints a plain-language definition,
how to author it, and its authoritative source (run `cds explain` for the whole list). Your AI
assistant can also explain any term in context.

## 5. Author your first mapping

**Recommended order:** problem → mission → goals → objectives → stakeholders → needs (a record can
link to ones you made earlier). Below, `main` is the slug for your mapping — you pass it as
`--synthesis main` on everything you add to it. (The README Quickstart is the same sequence, shorter.)

```bash
cds synthesis main --title "My project"

cds new problem p1 --synthesis main \
    --label "Too hard to reach a person" \
    --description "People get stuck in automated menus and give up."

cds new mission core --synthesis main \
    --label "Reach a human" \
    --description "Get a person to a verified human, cutting through the automation."

cds new goal reach --synthesis main --addresses p1 \
    --label "Reach" --description "Connect the seeker to a verified human."

cds new stakeholder seeker --synthesis main \
    --label "Seeker" --description "The person trying to reach a human." --segment elderly

cds new need n1 --synthesis main --for-stakeholder seeker --serves-goal reach \
    --label "Effortless reach" \
    --description "The seeker needs the system to connect them without technical skill."
```

**Needs use "need form," never "shall"** (requirements come in a later stage). Describe what the
stakeholder *needs*, not what the system *shall* do:

- ✅ *"The seeker needs the system to connect them without technical skill."*
- ❌ *"The system shall connect the seeker within 30 seconds."*

`cds verify` flags a need written with "shall" and shows you the fix.

Review what you've recorded any time:

```bash
cds list need
cds show need n1
```

## 6. Check and compile

```bash
cds verify     # flags common slips: 'shall' in a need, needs with no stakeholder, duplicates
cds compile    # writes concept-definition/briefs/concept-definition.md
```

Open the brief — that's your shareable concept definition.

## 7. Changing your mind

You will. Re-run `cds new` with the **same slug** and corrected values — it *replaces* the record
(no duplicates). To keep the change history, author a new record with `--supersedes <old-slug>`. To
delete, use `cds rm <kind> <slug>`. Never hand-edit the `.ttl` files — always go through the CLI.

## 8. Keeping the session clean

- A tangent or out-of-scope idea → `cds park add <slug> --label "…"`.
- An unknown you can't answer yet → `cds queue add <slug> --question "…"`.
- A real conflict between records → `cds tension add <slug> --label "…"`; resolve it later with
  `cds tension resolve <slug>`.

## Next steps

- The [User guide](user-guide.md) covers every command and the full workflow.
- `cds --help` lists everything; `cds <command> --help` explains each.
- The [Construction order](construction-order.md) explains the method the tool is built on.

## Troubleshooting

- **`command not found: uv`** — you don't have `uv` installed. Use the plain path instead:
  `python3.11 -m venv .venv && source .venv/bin/activate && pip install -e .`.
- **`no virtual environment found`** — create and activate one *before* installing:
  `python3.11 -m venv .venv` then `source .venv/bin/activate`, then `pip install -e .`.
- **Python too old (e.g. 3.9)** — cds needs **3.11+**. On macOS the system `python3` is often 3.9;
  install 3.11+ (e.g. `brew install python@3.11`, or from python.org) and use `python3.11`.
- **`cds: command not found` in a new terminal** — re-activate the env: `source .venv/bin/activate`.
