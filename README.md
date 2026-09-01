# PRAHARI

AI-assisted **preventive** oversight for the MPLAD Scheme.
Smart India Hackathon 2026 — MoSPI Problem Statement 26102.

MPLADS moves roughly ₹4,000 crore a year through thousands of small works.
Irregularities surface today through CAG audits, years after the money is spent.
PRAHARI screens a work **before sanction**, monitors it **after sanction**, tracks
whether the finished asset was ever handed to anyone, and puts what it finds in
front of a human reviewer who makes the actual decision.

```
recommendation ──► Stage 1 screening ──► sanction ──► Stage 2 monitoring ──► Stage 3 handover
                   cost · duplicate                   payment vs progress    handover recorded?
                   agency · compliance                geotag · variance      UC on file?
                   statistical                        timeline               register entry?
                          │                                  │                      │
                          └──────────────┬───────────────────┴──────────────────────┘
                                         ▼
                        composite score → severity tier → templated explanation
                                         ▼
                             a person decides: Investigate / Override / Clear
```

## What this system does not do

Load-bearing constraints, not disclaimers. Each is enforced somewhere you can point at.

| Rule | Where it is enforced |
|---|---|
| **Never alleges wrongdoing.** Every output is a risk indicator requiring human investigation. | `tests/test_vocabulary.py` fails the build if "fraud", "corrupt" or similar appears in any source file |
| **Never decides anything.** A flag cannot block, reject or cancel a work. | Only three transitions exist, all human: `INVESTIGATE`, `OVERRIDE`, `CLEAR` |
| **An override must be justified in writing.** | `POST /flags/{id}/review` returns **422** under 20 characters — at the API, not just the interface |
| **No supervised classifier.** No labelled dataset of MPLADS irregularities exists. | Detection is unsupervised (Isolation Forest) + deterministic rules + peer-group deviation |
| **Every finding explains itself with a checkable number.** | `app/engine/explain.py` — one template per flag code, filled from computed values. No language model in this path |
| **Agency records are peer-group relative and capped.** | Ranked only within terrain group; contribution clamped at 15% in `scoring.py` regardless of configured weight |
| **All data is synthetic.** | Non-dismissible badge on every screen |

## What is actually running

**The machine learning is live, not planned.** Two models run on every screening pass:

- **Isolation Forest** (scikit-learn, 200 estimators) — fitted on the population Stage 1 screens, scoring each proposal on cost ratio, peer deviation, agency record, member workload and location density. Reports a percentile, so "78" means *more unusual than 78% of comparable proposals*.
- **`all-MiniLM-L6-v2` sentence embeddings** — description similarity for duplicate detection, combined with haversine distance and a time window. Similarity alone is meaningless here; it only becomes a signal when two works are also metres apart and months apart.

Scoring 4,000 works takes about 35 seconds end to end.

## Measured, not asserted

Run `python -m app.engine.cli recall` to reproduce:

```
planted pattern      unit     n  caught   recall
COST_INFLATION       work    40      40  100.0%
DUPLICATE_WORK       work    40      40  100.0%
SALAMI_SLICING       work    41      41  100.0%
...  all 12 patterns pass
works with no planted anomaly   3277
of those, drew a finding         186  (5.7%)
```

**Read that honestly.** It measures the engine against anomalies this project
planted itself. It shows the detectors are wired to the patterns they were built
for and that a change has not silently broken one. It is **not** a measurement of
real-world accuracy, and the backtest screen says so in the words a juror reads.

## Status: what is built, what is scaffolding

### Working, on live data

| Area | State |
|---|---|
| Engine — 10 modules across 3 stages | Built, tested per module |
| Composite scoring, tiering, compliance override | Built |
| Templated explanations, 26 flag codes | Built |
| Synthetic generator, 4,000 works, 12 planted patterns | Built, deterministic under `--seed` |
| API — 25 endpoints | Built |
| Seven-role access model | Built, 43 boundary tests |
| Review workflow + audit trail | Built |
| All seven dashboards | Built, reading live endpoints |
| CSV export, fund-flow Sankey, national map, charts | Built |

### Scaffolding — designed, labelled, not wired

Each renders with a dashed border and a tag naming what it waits on.
**A placeholder never displays an invented number** — only the shape of a screen.

- Photo upload with server-side EXIF extraction *(needs Firebase)*
- Progress-report submission, agency responses to findings
- Flag reassignment UI *(the endpoint exists; only the button is a stub)*
- Escalation to Ministry, formatted PDF export
- Colab training notebook

### Not started

- `GET /backtest/cases`, `POST /backtest/run` — the backtest screen currently
  shows figures pasted from a CLI run rather than computing them live
- Schedule of Rates CSV loader (the generator synthesises rates)
- Cost-index loader and the real-terms Trends chart

## Running it

```powershell
# Backend
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\python.exe -m app.seed.generate --works 4000 --seed 42 --reset
.\.venv\Scripts\python.exe -m app.engine.cli score
.\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8001
```

```powershell
# Frontend, second terminal
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. Sign in as any of the seven roles — no password
is required until Firebase is configured, and the screen says so.

**Authentication is currently demo mode.** `/api/v1/health` reports
`"auth": "demo"`: the backend accepts a named account without checking a
password. The *access rules* behind it are real and tested. See
`docs/FIREBASE_SETUP.md` to switch it on — about 25 minutes in a browser.

## Reading the code

Start here, in this order:

| File | Why |
|---|---|
| `backend/app/engine/explain.py` | The templates. Shows what a finding is allowed to say |
| `backend/app/engine/stage1/cost_benchmark.py` | The clearest module. Also where the inflation defence lives |
| `backend/app/engine/scoring.py` | The three rules beyond a weighted sum, each with its reason |
| `backend/app/api/deps.py` | `Scope` — the seven-role access model, in one class |
| `backend/tests/test_access_boundaries.py` | What the system refuses to show, proved by real HTTP requests |
| `frontend/src/components/ui-kit.tsx` | `ThresholdBar` — the evidence row every finding renders through |

Every non-obvious decision is recorded in `DECISIONS.md` with the reason and,
where it was found by measurement, the number that prompted it.

## Testing

```powershell
cd backend
.\.venv\Scripts\pytest.exe               # 121 tests
.\.venv\Scripts\pytest.exe -m "not slow" # skips the seed-and-score integration test
```

## Layout

```
backend/app/
  engine/stage1/   cost_benchmark · duplicate_detection · agency_performance
                   compliance_rules · isolation_forest
  engine/stage2/   payment_progress · geotag_verification · cost_variance · timeline
  engine/stage3/   handover
  engine/          scoring.py · explain.py · context.py · similarity.py · cli.py
  api/v1/          works · dashboards · lifecycle · system
  api/deps.py      authentication and the seven-role Scope
  models/          20 tables
  seed/            synthetic generator + catalogues
  config/          weights.yaml — defaults; the database wins once seeded
frontend/src/
  pages/           one directory per role
  components/      ui-kit.tsx carries every shared primitive
  api/             client · hooks · types
docs/
  FIREBASE_SETUP.md   browser steps, assumes no prior Firebase experience
  EXTERNAL_SETUP.md   everything else outside the editor
DESIGN.md             the visual system and why each choice was made
DECISIONS.md          every departure from the specification, with its reason
```

## Branches

- **`prototype`** — the earlier UI-only prototype, placeholder data, no engine
- **`MVP`** — this. Full engine, API, seven roles on live data
