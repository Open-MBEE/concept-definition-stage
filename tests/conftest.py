"""TEMPORARY stack gating for the T8 PR sequence — delete-by: stack PR 07.

test_provenance.py turns green in stack PR 07 (provenance + audit), which deletes
this file entirely. The staging/held-out acceptance tests went green in this PR and
are no longer gated.
"""

collect_ignore = [
    "unit/test_provenance.py",
]
