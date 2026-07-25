# Session S1 — Tool-lending library ("Dana")

**Human persona:** Dana, a non-technical community organizer starting a neighborhood tool-lending
library. **Facilitator:** followed the vendored `cds-elicit` skill against the real CLI.
**Behaviors injected:** tangent, genuine unknown (insurance/liability), buyer≠user (borrower vs.
funder), a "shall" slip, a reversal (free → small annual fee).

**Recorded:** 1 problem, 1 mission, 3 goals, 6 objectives, 3 drivers, 3 constraints, 3 MoEs, 5
stakeholders (funder/user split), 10 needs, 2 parked, 1 queued (insurance), 1 tension.

## Friction log (facilitator, verbatim)

1. **[MAJOR] `cds new` has no update/overwrite semantics — and no `cds edit`/`update`/`rm`.**
   Re-running `cds new` with an existing slug does NOT replace the record; it APPENDS. After
   re-running a need to fix wording, it ended with TWO `dcterms:description` values (old + new).
   Combined with the skill's "never hand-edit the Turtle", there is literally **NO sanctioned way to
   correct a mistyped/misworded record.** The single biggest gap.
2. **[BUG] The verify "shall" check is a naive substring match over the ENTIRE description.** It
   flagged a need whose *meta-note* merely contained the word "shall" — the actual need clause was
   clean need-form. False positive (its manifestation here came from the doubled description in #1).
3. **[BUG vs SKILL PROMISE] No orphan-need detection for a need with a stakeholder but no goal.** A
   need left with no `--serves-goal` was NOT flagged, though the skill promises verify surfaces
   "orphan needs".
4. **[VISIBILITY] `cds new` prints only the resulting IRI** — no echo of stored fields, so the
   append-vs-overwrite behavior (#1) is invisible unless you read the raw TTL.
5. **[MISSING] No `cds list`/`show` to review captured content mid-session** — only option was to
   grep the `.ttl` files.
6. **[LEAK] The duplicate-description bug (#1) leaks into the human-facing brief;** and there is no
   separate "scribe note" vs "content" field, so facilitator commentary ends up in the description
   that's shown to the human.
7. **[SKILL] `compile` gated behind a stale "when M5 lands" conditional** — compile worked fine.
8. **[SKILL] "one question at a time / never batch" vs. flow.** Strictly one-at-a-time for 5 goals or
   one-need-per-stakeholder is painfully slow. Compromise (batch elicitation, record atomically)
   worked but the skill gave no guidance.
9. **[MINOR] `--addresses` not mentioned in the skill's construction-order list.**
10. **[MINOR] Terse success output means a typo'd kind could silently create a weird record** (kind
    is validated, but the terseness hides mistakes).

*Overall:* the elicitation model + vocabulary are excellent and the skill is very followable for a
first pass. The critical missing piece is any way to CORRECT a record without hand-editing Turtle
(#1), plus read-back (#5) and the two verify issues (#2, #3).

## `cds verify` (final)

```
[T2] …/need/borrower-reserve-ahead — need uses 'shall' — needs use need-form, not requirement-form
verify OK — 1 warning(s), 0 lint.
```

(The lone warning is the false positive from #1/#2 — a leftover appended description mentioning
"shall", uncorrectable without hand-editing.)

## Compiled brief (excerpt)

```
# Tool Library
*Concept Definition — Business Analysis & Stakeholder Needs*

## Business / Mission Analysis
### Problem
- Wasteful duplicate ownership of rarely-used tools — neighbors each buy expensive tools used
  once or twice a year; those who can't afford them go without.
### Mission
- Let neighbors borrow good tools cheaply and easily; keep them well-maintained.
### Goals
- Financially/operationally sustainable · Tools stay safe & in good shape · Wide neighborhood access
### Objectives
- Membership fees (~$20/yr) + grants cover running costs (refines: sustainability)  [the reversal]
- Tool available within a day or two (refines: wide-access)
- ≥200 households enrolled year one (refines: wide-access)  … etc.

## Stakeholders
| Borrowers (users) | Funders (grant + board, High influence) | Volunteer repair crew | Host | Neighborhood |

## Integrated Set of Needs
- Borrower: affordable incl. fee waiver; book ahead; safe use; see/borrow without hassle
- Repair crew: know what's returning damaged; manageable workload; place + parts to fix
- Funder: money spent responsibly; Host: space respected; Neighborhood: be a good neighbor

## Tensions
- Membership fee vs. free universal access

## Parking-lot
- Feel more connected; expand beyond tools (repair workshops, camping gear, seed library)

## Open Items (Retrieval Queue)
- [pending] How do insurance and liability work for a neighborhood tool library?
```
