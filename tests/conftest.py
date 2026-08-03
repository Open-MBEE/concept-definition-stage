"""TEMPORARY stack gating for the T8 PR sequence — delete-by: stack PR 07.

These acceptance tests were authored up front (red-first, spec §10) and turn green in
later PRs of the stack. Ignoring them here keeps every stack PR's test run green
without touching the test files themselves:

- test_staging_commit.py, test_held_out.py: green in stack PR 06 (session staging +
  commit gate), which removes their entries.
- test_provenance.py: green in stack PR 07 (provenance + audit), which deletes this
  file entirely.
"""

collect_ignore = [
    "unit/test_held_out.py",
    "unit/test_staging_commit.py",
    "unit/test_provenance.py",
]
