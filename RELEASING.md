# Releasing cds — v0.2 plumbing runbook

Goal: ship a **public v0.2** — installable from **PyPI**, with the **Sphinx docs published to GitHub
Pages** and **green CI** (matrix + determinism). This runbook sequences the release plumbing so it can
be picked up in any future session. Each step links its tracking issue on the
[**v0.2 milestone**](https://github.com/Open-MBEE/concept-definition-stage/milestone/1).

**Pick-up-here for a future session:** read this file top to bottom. Start at §1 (CI). **Do not publish
to PyPI until §0 is resolved** — it's a legal gate.

---

## 0. BLOCKER — canon redistribution (resolve before any publish) · #2

The wheel currently ships `src/cds/ontology/concept-definition.ttl`, which **materializes verbatim
SEBoK/INCOSE definitions** (SEBoK is **CC BY-NC-SA**). Publishing that file to PyPI is
**redistribution** of restricted text — the "text in the model, cite in the view" argument (RDF isn't
human-consumable) does **not** cover shipping it in a public package.

Decide, and record the decision in the PR that resolves #2:

- **(a) Ship cite-only canon** (recommended): the *distributed* artifact strips the verbatim
  `skos:definition` / `cds:quote` text and keeps locators + citations. Options: a build step that emits
  a redistributable `concept-definition.ttl` (definitions removed) for packaging, or gate packaging on
  the operator's `text_license`. `cds verify` needs shapes, not the verbatim, so this is safe;
  `cds explain` already cites rather than reproduces.
- **(b) Confirm permission** for the specific text + ship proper `NOTICE`/attribution (ShareAlike
  implications — the wheel would inherit BY-NC-SA, which conflicts with the Apache-2.0 code license).

**Until (a) or (b) is done, PyPI publish (#6) is blocked.** This is the single most important item.

---

## 1. CI hardening · #1

`ci.yml` already runs `ruff` + `mypy` (strict, incl. tests) + `pytest` and is green on `main`. Remaining:

- **Matrix:** run on Python **3.11 and 3.12**.
- **Determinism job:** regenerate the committed artifacts and fail on drift —
  `cds build` (and `python -c "from cds.core.vocabulary import write_core_ttl; write_core_ttl()"`),
  then `git diff --exit-code -- src/cds/ontology/*.ttl`. (The packaged-guide DRY check is already a
  unit test.)
- **Docs build check** (optional but cheap): `uv pip install -e .[docs]` + `sphinx-build -b html docs
  /tmp/site` so doc breakage fails CI.

**Done when:** green matrix CI on `main` + the determinism job guards the committed `*.ttl`.

## 2. Distribution name · #33

The import name stays `cds`, but the **PyPI distribution name** `cds` is almost certainly taken. Decide
+ reserve one (e.g. `concept-definition-stage`, `openmbee-cds`, `cds-mbee`). Set `[project].name` to it
(keep `packages = ["src/cds"]` so `import cds` is unchanged), and update the install lines in `README.md`
and `docs/getting-started.md` to `pip install <name>`.

## 3. Packaging validation · #6 (prep)

- **`pyproject.toml`:** add `[project.urls]` (Homepage, Repository, Documentation, Issues), `classifiers`
  (Python versions, license, topic), confirm `readme`/`license`/`requires-python`/`keywords`.
- **Confirm package-data ships** (this bit us before — canon is under the package now): build and inspect.
  ```bash
  uv build
  python -m zipfile -l dist/*.whl | grep -E "ontology/|assets/|terms/|characteristics.yaml"   # must be present
  pipx run twine check dist/*
  ```
- **Clean-room install test** (no repo):
  ```bash
  python3.11 -m venv /tmp/relv && . /tmp/relv/bin/activate && pip install dist/*.whl
  cds --version && cds explain need && (cd $(mktemp -d) && cds init --name t && cds guide >/dev/null)
  ```
- **Done when:** a wheel that installs into a fresh env and runs `init`/`explain`/`guide`/`verify`/
  `compile` with no repo present.

## 4. PyPI publish via OIDC trusted publisher · #6

- Register the project on **TestPyPI** and **PyPI** (reserving the §2 name). Configure a **Trusted
  Publisher** (OIDC — no API tokens): owner `Open-MBEE`, repo `concept-definition-stage`, workflow
  `release.yml`, environment `pypi` (and a `testpypi` one for dry-runs).
- Add `.github/workflows/release.yml`: trigger on tag `v*`; build sdist+wheel; publish with
  `pypa/gh-action-pypi-publish@release/v1`; `permissions: { id-token: write }`; `environment: pypi`.
  **Dry-run to TestPyPI first** (same action with `repository-url: https://test.pypi.org/legacy/`).
- **Release flow:** finish §6 gates → bump version (#4) → tag `vX.Y.Z` → push tag → workflow publishes.
- **Done when:** `pip install <name>` from PyPI works after a tag.

## 5. Docs → GitHub Pages · #8

- Add `.github/workflows/docs.yml`: on `push: main` (+ `workflow_dispatch`) — `uv pip install -e .[docs]`;
  `sphinx-build -b html docs docs/_build/html`; upload with `actions/upload-pages-artifact` +
  `actions/deploy-pages`. `permissions: { pages: write, id-token: write }`; a `concurrency` group.
- Repo **Settings → Pages → Source: GitHub Actions**.
- Add the published URL to `README.md` and `pyproject`'s Documentation URL.
- **Done when:** a live docs site updates on push to `main`. (Independent of PyPI — can land in parallel.)

## 6. Release-readiness gates (bundle with the version tag)

- **#4 versioning:** bump `version` to `0.2.0`; add a `CHANGELOG.md` `[0.2.0]` entry (local-package
  engine, correction safety, learner CLI, onboarding + Sphinx docs).
- **#2 license/NOTICE:** land the §0 decision; add/verify `NOTICE`; keep `THIRD_PARTY_LICENSES.md` current.
- **#3 governance:** author/copyright reconciliation; `CODE_OF_CONDUCT.md` present.
- **#5 source-acquisition doc:** the operators-hold-the-PDFs (REFERENCE tier) doc.

---

## Suggested order

1. **#1 CI hardening** (matrix + determinism) — foundation; do first.
2. **§0 + #2** canon-redistribution decision — the legal gate; must precede any publish.
3. **#33 name** → **#6 packaging validation** → TestPyPI dry-run.
4. **#8 Pages** — parallel-safe, do whenever.
5. **#4 version bump + CHANGELOG** → tag → **#6 PyPI publish**.

Then the milestone's remaining `#3`/`#5` docs, and the release is out.

## Housekeeping

- Turn on **Settings → General → "Automatically delete head branches"** so merged PR branches don't
  accumulate (this caused branch residue in the v0.2 dev push).
- Keep chunked PRs **based on `main`** (not stacked on each other) — stacked PRs merged into their
  intermediate bases last time and left `main` missing commits until a remediation PR.
