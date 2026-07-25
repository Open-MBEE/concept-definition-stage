# Session S2 — Apartment EV-charging scheduler ("Priya")

**Human persona:** Priya, a detail-oriented engineer/PM for a shared EV-charging scheduler (many EV
owners, few chargers, limited panel). **Facilitator:** followed `cds-elicit`, batched for efficiency,
and deliberately probed relations + the update path. **Behaviors injected:** dense relations, a
**reversal on a related record** (equal-split → usage-based cost), a genuine unknown (panel
headroom), a tension, a parked tangent (solar+battery), plus a duplicate-slug probe on park/queue.

**Recorded:** problem, mission, 3 goals (`--addresses` problem), 3 objectives (`--refines` goals), 2
constraints, 1 driver, 1 MoE; 4 stakeholders (EV-owners=user vs. HOA-board=funder); 5 needs (each
`--for-stakeholder` + `--serves-goal`); reversal, tension, queue, park.

## Friction log (facilitator, verbatim)

1. **[SEVERE BUG] No edit/rm/upsert — re-authoring MERGES, it does not replace.** The reversal
   (equal-split → usage-based cost need) can only be done by re-running `cds new` on the same slug.
   The record then carries TWO `rdfs:label` AND TWO `dcterms:description` values (old + new). The
   subject IRI appears once, so `grep -c` looks fine — but the graph now asserts BOTH the superseded
   "split equally" wording AND the new "usage-based" wording. **The contradiction we were resolving
   is baked INTO the data.** No `edit`/`rm`/`supersede`/`deprecated` anywhere.
2. **[BUG] Same append-on-same-slug bug affects `park add` and `queue add` too.** Re-adding a park
   and a queue item with the same slug appended a second label/note. Universal upsert failure.
3. **[BUG] `list`/`compile` MASK the duplication by emitting the alphabetically-first value** — not
   latest-edit-wins. The queue Open Item in the brief showed the probe's garbage; park showed the OLD
   value. Corruption is invisible in the human-facing output.
4. **[VERIFY FALSE-NEGATIVE] `verify` reports 0 warnings / 0 lint on the corrupted graph.** No
   max-count on `rdfs:label` / `dcterms:description`, so two conflicting values pass clean.
5. **[CONFUSING] `build` and `verify` report different counts** for the "same" tri-severity check
   (`build`: "6 warning(s), 36 lint" on the vocabulary; standalone `verify`: "0/0" on the project).
   They validate different graphs; the output doesn't say which.
6. **[GAP] No way to close/resolve a tension.** After the reversal the logged tension still cited the
   superseded framing and still rendered. `tension` only has `add`.
7. **[MINOR] Slug becomes a misleading label after a reversal** — `need/equal-cost-split` now holds
   usage-based content; slugs are immutable ids, so list/log lines read backwards.
8. **[POSITIVE] Relations render correctly** — `--refines`, `--for-stakeholder`, `--serves-goal`,
   `--addresses` all persisted and show in the brief; the stakeholder table is clean. The connected
   graph is intact; the reversal is the only wound.

*Coping strategy:* with no edit, the facilitator re-authored then had to open raw `need.ttl` to SEE
the merge damage (the CLI never reported it), and could not cleanly retract the old values.

## `cds verify` (final)

```
verify OK — 0 warning(s), 0 lint.
```

(False-negative from #4 — the graph contains doubled labels/descriptions verify does not catch.)

## Compiled brief (excerpt)

```
# EV Charging Concept Definition
## Business / Mission Analysis
### Problem — ~40 EV owners share 4 Level-2 chargers on a panel that can't run all at once…
### Mission — Fairly schedule access + allocate cost within safe limits
### Goals — Accurate cost recovery · Fair, predictable access · Stay within panel capacity
### Objectives — 2+ sessions/week (refines fair-access) · billing within few % (refines cost-recovery)
             · draw ≤80% panel (refines within-capacity)

## Stakeholders
| Electric utility (external) | EV owners (User) | HOA board (Funder/decider, High) | Non-EV residents |

## Integrated Set of Needs
- EV owners pay for their own metered usage — REVISED (supersedes 'split equally…')  [the reversal]
- Fair predictable turn · Recover full cost · Never exceed limits · Never strand a car

## Tensions — Equal split vs. metered/defensible billing  [STALE: still cites superseded framing]
## Parking-lot — Rooftop solar + battery storage  [brief shows OLD label; 2nd corrupt value hidden]
## Open Items — [pending] DIFFERENT question text on re-add…  [CORRUPTED by probe; real question hidden]
```

*Headline:* the tool cannot safely correct a record — every mutation path (new/park/queue) appends
instead of upserts, verify doesn't catch the resulting contradiction, and the brief hides it by
picking one value alphabetically.
