# Retrieval queue (human-retrieval escalation — local fallback)

The agent **never fabricates canon**. When required canonical content is not yet secured, it is escalated to
a human here (and/or as a `retrieval` GitHub issue once the remote exists). The dependent term is **held out
of the build** until the artifact is provided and verified.

- **text** → wiki source grab (paste verbatim `{{...}}` wikitext) → `terms/<slug>.src.wiki`
- **image/figure** → screenshot → content-addressed snapshot in `sources/` (`sourceType=image`) + caption

**Status:** `pending` → `provided` → `verified`. A term builds only when `verified`.

| Term / artifact | Authority | Source URL | Artifact type | Status | Notes |
|---|---|---|---|---|---|
| _(none yet — populated during slice 6)_ |  |  |  |  | SEBoK v2.14 PDF is the primary source of record; this queue is the fallback for anything not in the PDF |
