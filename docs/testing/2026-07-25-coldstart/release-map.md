# Release map — PR-clusters → issues → commits

For the later push. Each **logical PR** below bundles a cluster of already-committed work on
`feat/local-package-mapping`; its body should `Closes #N` so merging closes the issue. Milestone:
**v0.2 — installable package + onboarding (PyPI + Sphinx docs)** (#1).

| PR (proposed) | Closes | Commits |
| --- | --- | --- |
| Local-package authoring engine (M0–M5) | #22 (progresses #14, #16) | `293e771` `0d1a2d0` `4ac7274` `dea6435` `3a0844e` `a674b12` |
| Correction safety (upsert / rm / read-back / verify guards) + decisions | #23 | `0477229` `673c2db` |
| Correctness: link validation, dangling-ref, clean errors | #24 | `3a1ade3` |
| Learner CLI: explain / guide / --version + plain help | #25 | `6781f4d` |
| `cds init` vendors neutral AGENTS.md | #26 | `4ca78d4` |
| Onboarding docs + Sphinx docsite | #27, **#8** | `1051974` `09a2ee9` |
| Testing records + onboarding benchmark | #28 | `bb594df` (+ the testing dirs in `673c2db`) |

Notes:

- These PRs are **not opened yet** (this session made no PRs). Sequence suggestion: engine (#22) →
  correction (#23) → correctness (#24) → learner (#25) → vendoring (#26) → onboarding+docs (#27/#8) →
  records (#28). Each is independently reviewable; later ones build on earlier.
- **Already closed** by this session's work (not by a PR): #12 (T9) and #20 (X6).
- **Milestone issues that remain future work** (not closed by the above PRs): #6 PyPI (T1, see also
  #33 name guard), #1 CI, #2 license/NOTICE, #3 governance, #4 versioning/CHANGELOG, #5 source-
  acquisition, #8 Sphinx **publish** (the scaffold is done; hosting remains), #14 hosting, #16 v0.2
  umbrella. These are the rest of the milestone's acceptance criteria.
- **Recommendation issues** (unmilestoned, from the cold-start findings): #29 MOE traceability, #30
  ConOps kind, #31 interactive term-teaching, #32 ordering-trap coaching, #33 PyPI name guard.
