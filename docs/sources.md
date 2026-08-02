# Source acquisition

`cds` uses two tiers of source material:

| Tier | What | Vendored? |
|------|------|-----------|
| **REFERENCE** | Operator-held PDFs (SEBoK v2.14, GtWR v4 summary) | **No** — obtain independently |
| **COMMITTED** | Verbatim definitions materialized in `ontology/concept-definition.ttl` | Yes — in the repo |

REFERENCE-tier files are **not distributed** with cds. Operators obtain them independently and
point cds to them via environment variables. This is consistent with the source license terms.

---

## SEBoK v2.14 (Systems Engineering Body of Knowledge)

**License:** CC BY-NC-SA 4.0 (SERC / Stevens Institute of Technology)

**How to obtain:** Download the PDF from [sebokwiki.org](https://sebokwiki.org/) (free, requires
registration). The version used to build `concept-definition.ttl` is **SEBoK v2.14**.

**Expected SHA-256:**
```
0bf5918db034757fb63fb81a677263ebe36323eee95e51fbd0197aecdd574176
```

The file in `sources/` is named by this hash. Verify your copy:
```bash
shasum -a 256 /path/to/sebok-v2.14.pdf
```

**Environment variable** (for faithfulness tests):
```bash
export SEBOK_PDF_PATH=/path/to/sebok-v2.14.pdf
uv run pytest tests/interop/test_faithfulness.py
```

---

## GtWR v4 summary (INCOSE Guide to the Roadmap)

**License:** INCOSE custom — reproduction with attribution permitted for non-commercial use.

**How to obtain:** Contact INCOSE or download via your INCOSE member portal. The version used
is the **GtWR v4 summary sheet** (one-page characteristic-statements PDF).

The GtWR faithfulness tests run against a committed snapshot stored as a content-addressed file
in `sources/` — no separate env var is needed for those tests. The SEBoK PDF is the only
operator-provided file required for the full faithfulness suite.

---

## Verification

To verify your local copy matches the committed snapshot used to build the vocabulary:

```bash
# SEBoK PDF
shasum -a 256 /path/to/sebok-v2.14.pdf
# should match: 0bf5918db034757fb63fb81a677263ebe36323eee95e51fbd0197aecdd574176

# Run faithfulness tests (requires pdftotext in PATH)
SEBOK_PDF_PATH=/path/to/sebok-v2.14.pdf uv run pytest tests/interop/test_faithfulness.py -v
```

---

## What "REFERENCE tier" means

In the `cds` model, a source with `retrieval_tier = REFERENCE` is:

- Verified at build time against its `content_hash`.
- Not committed to the repository.
- Expected to be present on the operator's local filesystem.

This is the standard pattern for standards-body documents where redistribution is restricted.
The verbatim definitions materialized in `ontology/concept-definition.ttl` are covered by the
source authority's license (see `THIRD_PARTY_LICENSES.md`). The tooling (Python, SHACL shapes,
CLI) is Apache-2.0.

## Seeing the standard: cite-only floor, attestation, propagation

You can never be fully blinded from a standard by license settings ("you cannot follow
engineering best practices if you cannot see them"). Three layers:

1. **Cite-only floor (always available).** Under any text license, every term still
   renders with its label, structure, and a citation to the strongest grounding target,
   so you always know where the authoritative text lives.
2. **Noncommercial attestation (low-friction opt-in).** If your use is noncommercial
   (for example an accredited student design project), attest it and get the verbatim:

   ```bash
   cds render --attest-noncommercial "https://example.org/you" --attest-context "ABET senior design"
   ```

   The attestation is a recorded legal assertion: who, context, and the statement are
   appended to a hash-chained `views/attestations.jsonl` alongside the rendered files.
   (The attestation wording is a draft pending legal review.)
3. **License propagation (automatic).** Any output that embeds SEBoK verbatim, attested
   or not, is stamped CC BY-NC-SA at rest, whatever license you requested, so the
   derivative is correctly licensed instead of mislabeled permissive. NonCommercial is
   cleared by your attestation; ShareAlike is cleared by construction.
