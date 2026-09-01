# PRAHARI — honest status report

**Written:** 1 September 2026
**Branch:** `MVP` · repo `github.com/sarukeshray/PRAHARI`
**Purpose:** an accurate account of what exists, what works, what does not, and
what is misleading — for someone deciding what to do next.

This is deliberately not a pitch. Where something is weaker than it appears, it
says so.

---

## 1. What the project is

A two-stage — now three-stage — risk screening system for the MPLAD Scheme.
It screens a public work **before sanction**, monitors it **after sanction**,
checks whether the finished asset was ever formally handed to anyone, and routes
every finding to a human reviewer.

Seven roles, each seeing a different slice: District Authority, Member of
Parliament, Ministry (MoSPI), State Nodal Authority, Implementing Agency, User
Agency, and Public.

### Size

| | |
|---|---|
| Backend | ~6,700 lines Python (excluding tests) |
| Frontend | ~6,100 lines TypeScript (excluding shadcn primitives) |
| Tests | ~1,150 lines, **135 tests**, all passing |
| API | 36 endpoints |
| Database | 21 tables, 4,002 works, 1,350 findings, 8,077 photographs |
| Commits | 11, each gated on a verification step |

---

## 2. What genuinely works

Everything in this section has been exercised end to end against a running
server, not merely written.

### The engine — 10 modules across 3 stages

| Stage | Modules |
|---|---|
| 1 — pre-sanction | cost benchmark, duplicate detection, agency record, compliance rules, isolation forest |
| 2 — post-sanction | payment vs progress, geotag verification, cost variance, timeline |
| 3 — handover | handover recorded, UC on file, asset register entry |

Scoring 4,000 works takes ~35 seconds. 26 flag codes, each with a deterministic
templated explanation naming its number and its threshold.

### The machine learning is live, not planned

This is the most commonly misunderstood thing about the project, so state it
plainly: **two models run on every screening pass.**

- **Isolation Forest** — `app/engine/stage1/isolation_forest.py`. scikit-learn,
  200 estimators, `contamination=0.10`, fitted on the population Stage 1 actually
  screens. Score is a **percentile**, so "78" means *stranger than 78% of
  comparable proposals*.
- **`all-MiniLM-L6-v2` sentence embeddings** — `app/engine/similarity.py`. Real
  transformer inference over 4,000 descriptions for duplicate detection, combined
  with haversine distance and a time window.

The ~2.5 GB venv is torch. The 35-second scoring time is the models running.

### Access model

Seven roles, filters derived from the `users` table on the server, never from
anything the client sends. Verified live — each role returns a different slice of
the same corpus:

```
District Authority  334 works      Ministry      all
Member of Parliament 71 works      Public          0 works
Implementing Agency  72 works      User Agency    40 assets
```

A record outside scope returns **404, not 403** — a 403 would confirm it exists.

### Review workflow

Investigate / Override / Clear. An override under 20 characters is refused with
**422 at the API**, not merely disabled in the interface. Decisions are written to
an audit trail and **survive rescoring** (this was a real bug; see §5).

### Everything else confirmed working

- Photograph upload with **server-side EXIF extraction** (see §3 — this is the
  most defensible thing in the system)
- Progress reports; agency responses that never clear a finding
- Flag reassignment between reviewers
- Citizen submissions — public form, official inbox, reply
- CAG backtest, **computed live** in an isolated scratch database
- Method sensitivity, computed from the working corpus
- Audit-ready PDF, generated server-side
- CSV export on three screens
- Fund-flow Sankey, proportional-symbol national map, radar, bubble, gauge, box plot
- Leaflet district map with severity encoded by both colour and radius

---

## 3. The three things most worth defending in a technical conversation

### a) The inflation defence

A cost is compared against the Schedule of Rates **for its own year**. A uniform
price rise moves cost and benchmark together, so the ratio does not change and no
finding fires. It cancels arithmetically rather than approximately, and needs no
external index.

Verified on the corpus: median SoR rises **₹766,800 → ₹1,137,882** (+48% nominal)
across four years while the median cost ratio holds at **1.00**. Asserted by two
tests, one of which applies a district-wide rise and requires silence.

### b) Photograph metadata is read on the server

`POST /agency/works/{id}/photos` extracts GPS and capture time from the image
file with Pillow, **server-side**. Never from the client.

This is not a detail. The party uploading is exactly the party the geotag check
exists to verify. Extracting EXIF in the browser and posting the values — the
obvious, faster implementation — produces a control that catches only someone who
forgot to lie.

Verified: a JPEG carrying GPS 60 km from a work site was uploaded, the server read
the coordinates out of the file, and re-screening raised
`PHOTO_LOCATION_MISMATCH` quoting the distance.

### c) The agency signal is capped in code, not configuration

An agency is ranked only against agencies in the same terrain category — never
nationally — and its contribution is clamped at 15% of the composite **inside
`scoring.py`**, regardless of the configured weight. Tested by setting the weight
to 0.90 and asserting the contribution is still 15.

Without the cap, terrain becomes a permanent penalty an agency cannot escape by
performing well, and the penalty compounds because scrutiny produces findings.

---

## 4. What is NOT built or is weaker than it looks

### Authentication is demo mode

`/api/v1/health` reports `"auth": "demo"`. The backend accepts an `X-Demo-User`
header naming a seeded account **without checking a password**. It is not
authentication — it trusts the client entirely.

The *authorisation* rules behind it are real and covered by 43 tests. Firebase
code is written and `docs/FIREBASE_SETUP.md` is complete; it needs ~25 minutes in
a browser. The fallback refuses to run when `ENV=production`.

### The "100% recall" figures are self-graded

Every anomaly measured was planted by this project. The figures show the
detectors are wired to the patterns they were built for and that a change has not
silently broken one. **They say nothing about real-world accuracy.**

Two rows are statistically thin and should be described that way:
`ENTITLEMENT_BREACH` rests on **2 groups**, `QUOTA_SHORTFALL` on **1**.

### The notebook artefact instruction is currently misleading

`notebooks/prahari_model_training.ipynb` tells the reader to download
`isolation_forest.joblib` and place it at
`backend/app/engine/artifacts/isolation_forest.joblib`.

**Nothing in the backend reads that path.** The engine refits the model in-process
on every scoring run. Either the backend should load the artefact when present
(~20 minutes, and a better answer to "where does your trained model live?"), or
that cell should be reworded to say the artefact is for inspection only. **This is
a live inconsistency and should be resolved either way.**

### Schedule of Rates data is synthetic

The generator invents rates (a plausible base per work type, escalated 6.2% a
year, multiplied by a terrain factor). A loader for published state CSVs exists
(`python -m app.seed.load_reference_data`) and the format is documented, but no
real data has been supplied. Cost findings currently cite "a synthetic benchmark"
rather than a real Schedule of Rates edition.

### The severity palette fails colour-vision validation

MEDIUM amber and HIGH orange are **ΔE 0.7 apart under deuteranopia** and 8.2 for
normal vision — effectively the same colour. Three re-steppings failed
identically; amber, orange and red are near-collinear in hue.

Mitigated by redundant encoding: tier spelled out as text, solid vs outline fill,
marker radius on maps, and no chart that requires telling two warm tiers apart.
It works, but it depends on every future screen remembering the second encoding.
Recorded as D-006 and **still needs a decision**.

### Not started at all

- **Escalation to Ministry** — reassignment between reviewers works; a formal
  escalation path does not exist
- **Rate limiting** on `POST /public/submissions`, which is unauthenticated.
  Length caps bound one request; they do not bound a flood. Any real deployment
  needs this plus a captcha
- **Real-terms Trends chart** — hides itself until a cost-index CSV is loaded,
  rather than inventing a series
- **Deployment** — local only, by decision. Nothing is hosted

### No frontend tests

**Zero.** All 135 tests are backend. The React application has no unit tests, no
component tests, and no end-to-end tests. Every frontend bug found so far was
found by a human using the app — including a sign-in bug that sent every role to
the wrong dashboard.

### Not load tested

Never run against concurrent users. Scoring is single-threaded and takes 35
seconds; there is no queue, no background worker, and `POST /works/{id}/assess`
rebuilds the entire engine context on each call. It would not survive a room of
simultaneous users.

---

## 5. Bugs found and fixed — worth reading, they show where the risk lives

Each of these was found by **measuring or testing**, not by reading code. That
pattern is the main reason to trust the parts that are verified and to be
sceptical of the parts that are not.

| Bug | How it presented | Why it mattered |
|---|---|---|
| Reviewed findings did not survive rescoring | A CLEARED finding came back OPEN | The docstring claiming the behaviour sat directly above the ORM cascade that broke it |
| Every role signed in as whoever you were last | MP, Ministry, etc. all landed on District Authority | Credential in a module variable React did not track, plus a 60 ms `setTimeout` race |
| `OUT_OF_CONSTITUENCY` fired on 59% of works | Generator assigned Members by state, not constituency | Would have made the compliance module look broken |
| `ENTITLEMENT_EXCEEDED` gave 1,307 findings for 17 real breaches | Group-level fact raised against every work in the group | Buried the signal it exists to surface |
| Isolation Forest put 6 of 4,000 works over the line | min-max normalisation as specified compressed the distribution | The published score corresponded to nothing a reader could name |
| The recency feature taught the model that new works are strange | 39% of proposals flagged | Only recent works await sanction, so recency correlated with being unscreened |
| `SANCTION_DELAY_45D` ignored sanctions granted late | Only checked pending works | The opposite of what the guideline is about |
| Backtest fixture artefacts | Duplicate detection fired on an inadmissible-works case | Would have read as a finding about the method rather than about the fixture |

### The false-positive story is worth knowing

The first full run reported a **27.7%** flag rate on clean works. Inspection showed
most of it was not engine error — genuinely overdue works, genuine entitlement
breaches, and photograph *donors* the engine correctly cannot distinguish from
copies.

The tempting fix was raising thresholds until the number looked good. That buys
the metric with real recall. Instead the **generator** was corrected so "clean"
means "crosses nothing": **27.7% → 5.7%**, with recall unchanged at 100%.
Excluding the agency signal — which fires structurally for the weakest fifth of
every peer group — it is **2.7%**.

---

## 6. Design constraints, and where each is enforced

These are the project's load-bearing rules. Each is enforced somewhere you can
point at, not merely stated.

| Rule | Enforcement |
|---|---|
| Never alleges wrongdoing | `tests/test_vocabulary.py` fails the build if "fraud", "corrupt" etc. appear in any source file. Verified non-vacuous against a deliberate violation |
| Never decides anything | Only three transitions exist, all human |
| Overrides need written justification | 422 at the API boundary |
| No supervised classifier | Unsupervised + deterministic rules + peer-group deviation |
| Every finding names a checkable number | `explain.py` — one template per code, no language model in the path. A missing template or parameter raises rather than rendering a gap |
| Agency records peer-relative and capped | Clamped in `scoring.py`, tested at weight 0.90 |
| A citizen submission is never a Work | Separate table. Only a Member may recommend; public input never enters the screening pipeline |
| All data synthetic | Non-dismissible badge on every screen, including every page of the PDF |

---

## 7. Known technical debt

- **`POST /works/{id}/assess` rebuilds the whole engine context per call** —
  loads every work, recomputes peer statistics. Fine for a demo, wrong for
  anything concurrent
- **The `/me` query is refetched per navigation** in some paths; `staleTime` is
  set but the cache is cleared aggressively on sign-in
- **No database indexes beyond the obvious** — never profiled against a realistic
  query load
- **SQLite, not PostgreSQL.** Models are portable and `docker-compose.yml` is
  committed, but PostGIS has never been exercised; spatial work is done in Python
  via `geo_utils.haversine_m`
- **Port 8000 was abandoned** for 8001 after an orphaned socket would not release.
  Cosmetic, but it is why the docs say 8001
- **Line endings** — the repo is normalised to LF via `.gitattributes`; Windows
  checkouts produce CRLF warnings on every commit. Harmless, noisy

---

## 8. How to run it

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\python.exe -m app.seed.generate --works 4000 --seed 42 --reset
.\.venv\Scripts\python.exe -m app.engine.cli score
.\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8001
```

```powershell
cd frontend
npm install
npm run dev          # http://localhost:5173
```

Useful commands:

```powershell
.\.venv\Scripts\pytest.exe                  # 135 tests
.\.venv\Scripts\python.exe -m app.engine.cli recall   # regenerate sensitivity
.\.venv\Scripts\python.exe build_notebook.py          # rebuild the Colab notebook
```

---

## 9. Where to look first

| File | Why |
|---|---|
| `backend/app/engine/explain.py` | What a finding is allowed to say |
| `backend/app/engine/stage1/cost_benchmark.py` | Clearest module; the inflation defence |
| `backend/app/engine/scoring.py` | The three rules beyond a weighted sum |
| `backend/app/api/deps.py` | The seven-role access model in one class |
| `backend/app/api/v1/agency.py` | Where the geotag control actually lives |
| `backend/tests/test_access_boundaries.py` | What the system refuses to show |
| `frontend/src/components/ui-kit.tsx` | `ThresholdBar` — the evidence row |
| `DECISIONS.md` | 30 entries; every departure from spec with its reason |

---

## 10. Summary judgement

**Strong:** the analytical core. The engine, the explanations, the access model,
the review workflow and the server-side EXIF control are real, tested, and
defensible under questioning. The verification discipline — measuring rather than
asserting — caught eight substantive bugs that reading the code did not.

**Weak:** authentication is demo mode; there are no frontend tests at all; the
recall figures are self-graded and two of them rest on n=2 and n=1; the Schedule
of Rates data is invented; and nothing has been load tested or deployed.

**Actively misleading and should be fixed:** the notebook instructs the reader to
place a model artefact at a path nothing reads.

**Honest one-line summary:** a working, well-tested analytical prototype with a
complete interface and a real machine-learning core, running on synthetic data,
behind a sign-in that does not yet check passwords.
