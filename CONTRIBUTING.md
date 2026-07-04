# Contributing to cds

`cds` is an Open-MBEE project. Contributions are welcome via pull requests.

## Quick setup

```bash
git clone https://github.com/Open-MBEE/cds
cd cds
uv sync --extra dev        # installs cds + test/lint/type-check tools
uv run pytest              # 109 tests, ~4 s
uv run ruff check .
uv run mypy
```

For live SysML v2 interop tests (roadmap T9):

```bash
cp .env.example .env       # fill in FLEXO_SYSMLV2_URL / FLEXO_SYSMLV2_TOKEN
uv sync --extra dev --extra interop
uv run --env-file .env pytest tests/interop/test_flexo_sysmlv2.py
```

## The inviolable rule: no fabricated canon

`cds` commits authoritative systems engineering canon (SEBoK, INCOSE GtWR, etc.) to
version-controlled RDF. **Every `skos:definition` or `cds:quote` must be verbatim text a human
retrieved from a named, verified authority.** See `AGENTS.md` for the full contract.

If a required definition is not yet secured:

- Open a retrieval issue or add a row to `docs/retrieval-queue.md`.
- Hold the term out of the build until the source is verified.
- Never paraphrase, infer, or fill in from memory.

## Construction order

Terms are built in a strict 7-stage precedence enforced by SHACL:

1. Register the `cds:Authority`.
2. Attach a `cds:Source` (pending → provided → verified).
3. Materialize the verbatim definition only on a verified source.
4. Create the `cds:Term` and `cds:cites` the source.
5. Ground the term (alignment edge) and optionally add a SysML v2 anchor.
6. Admit the term to a `cds:Synthesis`.
7. Render / export.

`cds verify` enforces this. A T1 violation (`sh:Violation`) fails the build and is never
waivable. T2/T3 findings can be suppressed with a first-class `cds:Waiver` (append-only, stored
in `ontology/waivers.ttl`).

## Authoring a term

1. Add a YAML source in `src/cds/stages/concept_definition/` following the existing pattern.
2. Run `uv run cds build` to compile YAML → RDF.
3. Run `uv run cds verify` — must be T1-clean.
4. Run `uv run pytest` — all tests must pass.
5. Optionally run `uv run cds render` to produce a PDF (requires `typst` binary).

Do not hand-edit the canonical `.ttl` files. The YAML term sources are the ergonomic surface;
the CLI compiles them.

## Pull request checklist

- [ ] `uv run pytest` passes (109+ tests, no new failures)
- [ ] `uv run ruff check .` clean
- [ ] `uv run mypy` clean
- [ ] `uv run cds verify` conforms (T1-clean)
- [ ] No fabricated or paraphrased canon (every definition traces to a verified source)
- [ ] New terms include authority + source + verified retrieval record

## Code style

- Python 3.11+, strict mypy, ruff lint.
- Line length 100. Imports sorted by ruff/isort.
- No comments unless the WHY is non-obvious. No multi-line docstrings for obvious functions.

## License

Contributions are licensed under Apache-2.0 (code) and, for any verbatim canon you introduce,
subject to the source authority's license (see `THIRD_PARTY_LICENSES.md`).
