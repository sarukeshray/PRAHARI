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
