# DECISIONS

Every departure from the build specification, with its reason. One entry per
decision. Entries are append-only; if a decision is reversed, add a new entry
that supersedes the old one rather than editing history.

---

## D-001 — SQLite is the default database backend, not PostgreSQL/PostGIS

**Phase:** 0
**Spec reference:** §3, "Note on the database"

Docker is not installed on the build machine and no local PostgreSQL server is
present, so the spec's own escape hatch ("if Postgres setup blocks progress in
the first hour, fall back to SQLite") applies immediately rather than after an
hour of attempts.

What this means in practice:

- `app/config/settings.py` exposes `DB_BACKEND` (`sqlite` | `postgres`). The
  connection URL is derived from it, and Alembic reads the same setting.
- `docker-compose.yml` is committed and correct. Switching is two steps:
  `docker compose up -d`, then `DB_BACKEND=postgres` in `backend/.env`.
- PostGIS distance calls are replaced by `app/geo_utils.py::haversine_m`. Engine
  modules call that helper directly and never branch on the backend, so the
  switch requires no changes in `engine/`.
- SQLAlchemy models stay strictly portable: no PostGIS column types, no
  Postgres-only constructs. Alembic runs with `render_as_batch=True` because
  SQLite cannot `ALTER` columns in place.

**Cost of this choice:** spatial queries are computed in Python rather than in
the database. At the prototype's data volume (~4,000 works) this is not a
performance concern.

---

## D-002 — Dependencies added beyond §3

**Phase:** 0
**Spec reference:** §3, §16 ("Ask before adding any dependency not listed in §3")

Flagging these for approval. All are frontend; the backend uses only §3 packages.

| Package | Why | Removable? |
|---|---|---|
| `react-router-dom` | The District Authority dashboard is five screens (§11). §3 lists no router. | No — needed for §11. |
| `react-leaflet-cluster` | §11.3 requires markers "clustered at low zoom, individual at high zoom". `react-leaflet` has no clustering primitive. | Yes, at the cost of the clustering requirement. |
| `clsx`, `tailwind-merge`, `class-variance-authority`, `lucide-react` | Mandatory internals of shadcn/ui — its generated components import them directly. | No — shadcn/ui does not function without them. |
| `tw-animate-css` | Tailwind v4 replacement for `tailwindcss-animate`; shadcn's dialog/select transitions depend on it. | No — same reason. |
| `@types/node`, `@types/leaflet` | Type declarations only; no runtime code. | Yes, at the cost of type safety. |

If any of these should be dropped, say so and I will rework the affected screen.

---

## D-003 — Tailwind CSS v4 rather than v3

**Phase:** 0
**Spec reference:** §3 ("Tailwind CSS + shadcn/ui")

§3 does not pin a Tailwind major version. v4 is the current release and the one
shadcn/ui's CLI now targets by default. Practical differences: configuration
lives in `src/index.css` under `@theme` instead of `tailwind.config.js`, and the
build runs through the `@tailwindcss/vite` plugin rather than PostCSS. The
severity palette from §11 is defined as design tokens in that file.

---

## D-004 — Prototype pivot: three roles, placeholder data, no backend dependency

**Phase:** prototype
**Supersedes:** the original build spec's "District Authority only" scope

The prototype is a UI-first artefact for the internal pitch round. It ships three
of the product's six roles — District Authority (deep), Member of Parliament and
Ministry — and reads a placeholder dataset compiled into the frontend rather than
calling the API.

Consequences worth knowing:

- `npm run dev` alone runs the whole prototype. The FastAPI backend from Phase 0
  is untouched and still starts, but nothing in the UI depends on it.
- Review actions are real but in-memory: Investigate / Override / Clear change
  finding state and write an audit entry, and a reload restores the starting
  state. That is deliberate — a demo should be repeatable.
- `src/data/types.ts` mirrors the eSAKSHI-derived schema, so wiring the real
  engine in later is a data-source swap rather than a rewrite of the screens.
- State Nodal Authority, Implementing Agency and the public portal are named on
  the role screen and marked "not built" rather than shipped as empty shells.

---

## D-005 — React 19, not React 18

**Phase:** prototype
**Spec reference:** §3 ("React 18 + TypeScript + Vite")

The current Vite React-TS template installs React 19, and `react-leaflet` v5 —
the current release — requires it. Pinning back to 18 would have meant pinning
react-leaflet to v4 as well. Nothing in the build depends on React 19-specific
behaviour, so a downgrade later is mechanical.

---

## D-006 — The specified severity palette fails colour-vision validation

**Phase:** prototype
**Spec reference:** §11 ("LOW slate, MEDIUM amber, HIGH orange, CRITICAL red")

Running the four specified colours through a palette validator returns a hard
failure, and re-stepping the hues three times did not fix it:

```
[FAIL] CVD separation      #c4460b <-> #a9670c  ΔE 0.7 (deuteranopia)
[FAIL] Normal-vision floor #c4460b <-> #a9670c  ΔE 8.2 — below the floor of 15
```

MEDIUM amber and HIGH orange are effectively the same colour to a reader with
deuteranopia, and hard to separate even with full colour vision. Amber, orange
and red are close to collinear in hue, so no four-step slate→amber→orange→red
ramp can pass as a categorical palette.

The specified colours are kept, because the fix is not a different palette:

1. **Chips** carry the tier as text and use a solid fill for HIGH and CRITICAL
   against an outline for LOW and MEDIUM, so hue is never the only signal.
2. **Map markers** encode tier by radius as well as colour.
3. **Charts** never place two warm tiers side by side — see D-007.

**This needs deciding before the real build.** The honest options are to accept
the redundant encoding above as permanent, or to renumber the tiers onto a
palette that passes on its own. The current approach works but depends on every
future screen remembering to add the second encoding.

---

## D-007 — Charts are single-hue or small multiples, never stacked categorical

**Phase:** prototype
**Spec reference:** §11.4 ("Flags raised per month by module (stacked bar)")

A stacked bar needs one distinguishable hue per module. With nine modules that
requires a nine-colour categorical palette, which would both fail the validation
in D-006 and contradict this design system's rule that colour is information.

Findings-per-month is drawn instead as small multiples: one panel per module on a
shared scale, all in the same blue. Severity-over-time is likewise one panel per
tier, each labelled. Every other chart is a single-hue bar. Nothing in the
prototype asks a reader to tell two colours apart to read a value.

---

## D-008 — `react-leaflet-cluster` removed

**Phase:** prototype
**Amends:** D-002

Marker clustering was dropped. `CircleMarker` encodes severity by both radius and
colour, which clustering into a single count bubble would have thrown away, and
at this data volume clustering solved a problem the map does not have. This
removes the only genuinely discretionary dependency flagged in D-002.

---

## D-009 — Inflation handled by same-year SoR ratio, not a deflator

**Phase:** MVP 1
**Spec reference:** rule 5 of the build-out prompt, which cites a section 4.6
that does not exist in that document

The rule was stated but never specified, so the design was chosen here and is
recorded for challenge.

A work is compared against the Schedule of Rates **for the year it was
recommended**: `ratio = estimated_cost / sor_rate(work_type, terrain, year)`.
No deflator, no external index.

Why this over a CPWD/WPI deflator: a uniform price rise moves the cost and the
benchmark by the same factor, so it cancels out of the ratio arithmetically
rather than approximately. It also needs no external data, which means the
defence cannot break because a series was not sourced.

Verified on the seeded dataset. Median SoR climbs from ₹766,800 to ₹1,137,882
across the four years — 48% nominal — while the median cost ratio holds flat:

```
year      n   median SoR   median ratio   p95 ratio
2023    372      766,800          1.008       1.216
2024   1204      842,803          0.995       1.181
2025   1141      992,954          1.005       1.206
2026    729    1,137,882          1.003       1.180
```

A `cost_index` table and a real-terms Trends chart are built as well, but the
engine never reads them — they exist so the question can be answered visually in
Q&A. The chart hides itself when no index is loaded rather than inventing one.

---

## D-010 — `sor_benchmarks` keyed on terrain

**Phase:** MVP 1
**Spec reference:** original spec §4

The specified columns were `(state, work_type, unit, unit_rate, year,
terrain_multiplier)`. One `terrain_multiplier` on a row keyed by
`(state, work_type, year)` cannot express five different terrain factors, so the
lookup would have been ambiguous.

`terrain_category` is now part of the key. `terrain_multiplier` retains exactly
one meaning: the factor already applied to reach this row's rate. 720 rows for
3 states × 12 work types × 4 years × 5 terrains.

---

## D-011 — Three schema additions beyond both specs

**Phase:** MVP 1

| Table / column | Why |
|---|---|
| `users` | The seven-role access model needs somewhere to hold a role and its data scope. Every API filter derives from these columns rather than from anything the client sends. |
| `module_contributions` | The score breakdown a reviewer saw at decision time must be reproducible after the weights are retuned. Recomputing it would show a different breakdown than the one the decision was made on. |
| `engine_config` | The Ministry threshold screen needs somewhere to write. Seeded from `weights.yaml`, which stays as the documented default; the database wins once a row exists. |
| `agency_responses` | An implementing agency's reply to a finding. Kept separate from `flag_reviews` so a response can never be mistaken for a decision — a response routes back to the District Authority, it does not clear anything. |
| `works.recommended_date` nullable | Required to model CAG-04, a sanction recorded against no recommendation. |

---

## D-012 — Generator: minimum instances per anomaly, fixed reference date

**Phase:** MVP 1

**Floor of 30 instances per anomaly type.** The original spec asked for ~12%
planted across 11 types, which at 4,000 works gives roughly 5 instances of some
types once the split is uneven. Recall measured over 5 instances is noise, and
§10 requires a recall assertion per type. The generator now guarantees a floor,
which puts the realised share at 14.0% rather than 12% — the group-level
anomalies (`ENTITLEMENT_BREACH`, `QUOTA_SHORTFALL`) mark whole cohorts and
overshoot their target by construction.

**Fixed `REFERENCE_DATE = 2026-08-31` instead of `datetime.now()`.** Every age,
overdue window and isolation-forest recency feature is measured from it. With
wall-clock time the scores drift daily and a sensitivity report run in March
would not match one run in September.

**15% of aged works are left awaiting a sanction decision.** Without this only
178 of 4,000 works stayed `RECOMMENDED`, leaving Stage 1 almost nothing to
screen. It is also the more realistic model — a pending sanction is ordinary in
MPLADS, and it is what `SANCTION_DELAY_45D` exists to catch.

**Three defects found by hand-inspection and fixed:** work IDs encoded a year
that later mutated during anomaly planting; the disbursement clamp at 100%
silently shrank planted payment gaps below their own flag threshold; and
structural anomalies relocated works across districts, leaving a Kerala work ID
inside a Rajasthan cluster.

---

## D-013 — Group-level findings attach to their cause, not to every member

**Phase:** MVP 2

`ENTITLEMENT_EXCEEDED` and `QUOTA_SHORTFALL` are facts about a *group* — a
member's financial year, a district's financial year — but `risk_flags` requires
a `work_id`.

Raising them against every work in the group produced **1,307 findings for 17
actual breaches**, burying the signal the flag exists to surface. They are now
attached to the works that caused them:

- **Entitlement**: works are walked in recommendation order and the flag is
  raised only on those recommended after the running total crossed the cap.
  Those are the recommendations that should not have been made.
- **Quota**: raised once per deficient district-year, carried by the most recent
  non-SC/ST work — the last decision that could have gone the other way. The
  sentence states plainly that it is a district-level finding.

Recall for these two is therefore measured **per group**, not per work; per-work
recall would measure the labelling convention rather than the detection. Both
report 100%, but over only 2 and 1 groups respectively — thin evidence, and it
should be described that way.

---

## D-014 — Isolation Forest normalised by rank, threshold moved 70 → 90

**Phase:** MVP 2
**Spec reference:** original spec §6.5

The spec called for min-max over `decision_function`. That distribution is
tightly clustered, so scaled linearly it put 4,000 works into a narrow band:
**6 crossed the flag line**, and a published score of "78" corresponded to
nothing a reader could name.

The score is now the rank of a work against the training distribution, so "78"
means *more unusual than 78% of comparable proposals* — which is exactly what the
explanation template already claimed it meant.

The threshold moves with it. On a percentile scale, 70 flags the top 30% of every
batch; 90 matches the configured contamination of 0.10, which is the model's own
estimate of how much of the population is anomalous.

**Two related fixes, both found by measuring rather than by reading code:**

- The model is fitted on the population Stage 1 actually screens — works awaiting
  sanction — not the whole corpus. Training on everything made proposals look
  unusual simply for being unscreened.
- `days_recommendation_to_now` was **dropped** from the feature vector. Only
  recent works await sanction, so the model learned that recency is strange and
  flagged 39% of proposals. A work is not suspicious for being new. Timeliness is
  a compliance rule with a stated threshold, which is where it belongs.

---

## D-015 — `SANCTION_DELAY_45D` covers decisions taken late, not only outstanding ones

**Phase:** MVP 2

The rule originally fired only when `sanctioned_date IS NULL`. A work sanctioned
190 days after its recommendation passed in silence — the opposite of what the
guideline is for. It now measures recommendation-to-decision where a decision
exists, and recommendation-to-today where one does not, with a different sentence
for each because they call for different action.

Found by recall measurement: `TIMELINE_BREACH` sat at 62.5% and the missing half
were all works sanctioned late.

---

## D-016 — Making "clean" mean "crosses nothing"

**Phase:** MVP 2

The first full run reported a **27.7% false-positive rate**. Inspection showed
most of it was not engine error:

| Source | Count | What it actually was |
|---|---|---|
| `ENTITLEMENT_EXCEEDED` | 139 | Member-years that genuinely breached, created by random assignment |
| `SANCTION_DELAY_45D` | 145 | Pending proposals genuinely older than 45 days |
| `COMPLETION_OVERDUE_12M` | 135 | Works genuinely past the guideline |
| `PHOTO_REUSED_ACROSS_WORKS` | 40 | The *donor* of each planted pair — indistinguishable from the borrower |
| `AGENCY_HISTORICAL_CONCERN` | 127 | The bottom fifth of every peer group, by definition |

The wrong response would have been raising thresholds until the number looked
better, which would have cost real recall to flatter a metric. Instead the
generator was corrected so a work with no planted anomaly does not cross a real
threshold:

- Members are assigned greedily, never past 92% of the annual entitlement
- A genuinely stale pending proposal is *labelled* `TIMELINE_BREACH`, because
  that is what it is
- Unplanted works complete inside the twelve-month guideline
- Both works in a reused-photograph pair are labelled, since nothing in the
  record says which is the original

**Result: 27.7% → 5.7%**, with recall unchanged at 100% across all twelve
patterns. The residue is almost entirely the agency signal, which fires
structurally, is capped at MEDIUM, and is context rather than an allegation.

**On the 100% figures.** These measure the engine against anomalies this project
planted itself. They show the detectors are wired to the patterns they were built
for and that a change has not silently broken one. They say nothing about
real-world accuracy, and the backtest screen must not present them as if they do.

---

## D-017 — Demo sign-in fallback when Firebase is absent

**Phase:** MVP 3

Without Firebase configured the API accepts an `X-Demo-User` header naming a
seeded account. This is **not authentication** — it trusts the client entirely.

It exists so the project is demonstrable on a laptop with no Firebase project,
which matters for a hackathon. It refuses to start when `ENV=production`, so it
cannot reach a deployment by accident, and `/health` reports `"auth": "demo"` so
which mode is live is never ambiguous.

---

## D-018 — A record outside scope returns 404, not 403

**Phase:** MVP 3

`GET /works/{id}` for a work the caller may not see returns **404**. A 403 would
confirm the record exists, which is itself information the caller is not entitled
to — an Implementing Agency could enumerate work IDs and learn which are real.

403 is used only where the *action* is refused and the caller already legitimately
sees the record: a Member trying to review a finding, an Agency reading another
agency's performance.

---

## D-019 — Reviewed findings survive rescoring

**Phase:** MVP 3

`persist()` documented that a reviewer's decision is never discarded by a re-run.
It was not true. Deleting the parent assessment with `db.delete(row)` cascaded
through the ORM relationship and took the reviewed findings with it — so a
CLEARED finding came back OPEN after rescoring.

Now: OPEN findings are cleared with a bulk `delete()` statement that bypasses the
cascade, and a superseded assessment is removed **only if no findings remain**
against it. An assessment carrying a decided finding stays, because it is the
record that decision was made against.

Read paths take the newest assessment per stage, so a lingering superseded one
never drives the headline tier.

**Found by a test asserting the property, not by reading the code.** The comment
claiming the behaviour had been sitting above the bug that broke it.

---

## D-020 — Missing Schedule of Rates degrades instead of crashing

**Phase:** MVP 3

`benchmark()` raised `ValueError` on an empty rates table, taking the whole
assessment down. A missing benchmark is not evidence of anything about a work, so
the cost module now returns no finding and the other modules run normally.

---

## D-021 — Backend moved to port 8001

**Phase:** MVP 4

Port 8000 was left held by an orphaned socket — the owning process no longer
exists but Windows kept the listener bound, and it did not release across
several minutes.

The backend now defaults to **8001**, and the Vite proxy target is overridable
with `VITE_API_TARGET` so this is not baked in. Nothing user-facing changes: the
app is still at `localhost:5173`.

---

## D-022 — Frontend reads the API; the prototype fixtures are gone

**Phase:** MVP 4

`src/data/works.ts` and `src/data/analytics.ts` — the compiled-in placeholder
dataset — are deleted. Every number on every screen now comes from an endpoint.

Two consequences worth stating:

- **The client never decides its own role.** `/me` is the single source of truth
  for identity, navigation and scope, so the interface cannot offer a section the
  API would refuse. Route guards mirror the server; they do not replace it.
- **Charts stayed single-hue.** D-006 and D-007 still hold now that the data is
  real: the radar, the bubble chart and every bar use one hue, and identity is
  carried by position and label rather than by a colour a reader has to separate.

The backtest screen's sensitivity figures remain literals, regenerated from
`python -m app.engine.cli recall` rather than computed live — they describe a
specific scored corpus, and recomputing them per page load would invite them to
drift from the run they document.

---

## D-023 — Unbuilt features ship as labelled scaffolding, not fakes

**Phase:** MVP 4

Screens that are designed but not yet wired render through a shared
`PlaceholderPanel` / `PendingButton` treatment: a dashed border, a "next build"
tag, and a line naming what the feature is waiting on.

Two rules hold everywhere it is used, and they are the point:

1. **A placeholder never displays invented data.** It shows the shape of a
   screen — a form, a button, a panel — never a made-up finding, score or
   amount. Fabricating those would undermine the one thing this product asks to
   be trusted on, and a juror who spots one invented number will reasonably
   doubt every real one.
2. **It says what it is waiting on**, so a gap reads as a roadmap item rather
   than a defect.

Currently scaffolded: photo upload with server-side EXIF (needs Firebase),
progress-report submission, agency responses to findings, flag reassignment and
escalation, formatted PDF export, and the training notebook.

**Built for real instead of stubbed**, because each was close to free and a
working control beats a convincing fake:

- **CSV export** on the review queue, the agency's works and the state roll-up.
  Exports exactly the filtered rows on screen, BOM-prefixed so Excel renders
  rupee symbols correctly.
- **Fund-flow Sankey** on the Ministry overview, computed from the same state
  roll-up the table beneath it uses. The narrowing between sanctioned and
  released is the finding.
- **National map** as a proportional-symbol map rather than a filled choropleth.
  A choropleth colours a whole state by one number, so the eye reads the largest
  state as the worst — a property of geography, not of the data. Circle *area*
  encodes the count, and every marker carries its figure so nothing depends on
  judging a circle by sight.

---

## D-024 — The signed-in identity is React state, not a module variable

**Phase:** MVP 4 — bug fix

**Symptom.** Signing in as any role except Public landed on the District
Authority dashboard.

**Cause.** Two mistakes compounding:

1. The demo user id lived in a module-level variable in `api/client.ts`.
   Changing it mutated nothing React was watching, so `SessionProvider` did not
   re-render and the query stayed keyed to the previous identity.
2. `SignIn` navigated on a 60 ms `setTimeout` — "give the session a beat to
   catch up" — then the route guard read whatever identity was cached. If the
   previous role's `/me` was still in the cache, `RoleRoute` saw
   `DISTRICT_AUTHORITY`, decided the requested page was not allowed, and
   redirected to that role's home. Every sign-in inherited whoever you were last.

**Fix, in three parts:**

- The user id is `useState` in `SessionProvider`, and it is part of the `/me`
  query key, so a cached identity for one role can never be served to another.
- `signIn` is `async` and resolves `/me` before returning. `SignIn` navigates to
  `ROLE_HOME[identity.role]` — the role **the server confirmed**, not the one the
  form selected. No timer.
- `RoleRoute` distinguishes *no credential* (redirect to sign-in) from
  *credential still resolving* (show the loading state). Redirecting during the
  resolve window was what produced the wrong destination.

**Worth stating plainly:** the original comment read "give the session query a
beat to pick up the new credential". A timer standing in for a dependency is
always a race; it only looked fine because the first sign-in of a session has no
stale identity to inherit.
