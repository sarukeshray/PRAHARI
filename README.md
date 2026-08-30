# PRAHARI

AI-assisted **preventive** oversight for the MPLAD Scheme.
Smart India Hackathon 2026 — MoSPI Problem Statement 26102.

MPLADS moves roughly ₹4,000 crore a year through thousands of small works.
Irregularities surface today through CAG audits, years after the money is spent.
PRAHARI moves detection earlier: it screens a work **before sanction**, monitors
it **after sanction**, and puts the resulting risk indicators in front of a human
reviewer who makes the actual decision.

## What this system does not do

These are load-bearing constraints, not disclaimers.

- **It never alleges wrongdoing.** Every output is a risk indicator, anomaly, or
  compliance violation requiring human investigation.
- **It never decides anything.** A flag cannot block, reject, cancel or freeze a
  work. It routes to a person. The only state transitions are human actions:
  `INVESTIGATE`, `OVERRIDE` (written justification required), `CLEAR`.
- **It does not use a supervised classifier.** No labelled dataset of MPLADS
  irregularities exists. Detection is unsupervised (Isolation Forest), plus
  deterministic rule checks, plus peer-group statistical deviation.
- **Every flag explains itself in plain language, with a checkable number.**
  Explanations are templated and deterministic — generated from computed signal
  values, never by a language model, so they are auditable.
- **All data here is synthetic.** There is no live eSAKSHI connection, and every
  data screen says so.

## Architecture

```
Synthetic eSAKSHI-shaped dataset  (planted, labelled anomaly patterns)
                 │
   ┌─────────────┴─────────────┐
   │                           │
Stage 1: pre-sanction     Stage 2: post-sanction
COST · DUPLICATE ·        DISBURSEMENT · TIMELINE ·
COMPLIANCE · AGENCY ·     GEOTAG · VARIANCE
STATISTICAL
   │                           │
   └─────────────┬─────────────┘
                 │
   Composite score → severity tier → templated explanation
                 │
      FastAPI  →  District Authority dashboard  →  human review
```

## Running it

**Backend**

```bash
cd backend
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt   # Windows
alembic upgrade head
./.venv/Scripts/uvicorn.exe app.main:app --reload --port 8000
```

API docs at http://127.0.0.1:8000/docs, health at `/api/v1/health`.

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

Dashboard at http://localhost:5173 — `/api` is proxied to the backend.

**Database.** Defaults to SQLite, so no container runtime is needed. For
PostgreSQL + PostGIS: `docker compose up -d`, then set `DB_BACKEND=postgres` in
`backend/.env`. See `DECISIONS.md` D-001.

## Layout

```
backend/app/
  engine/stage1/   cost_benchmark · duplicate_detection · agency_performance
                   compliance_rules · isolation_forest
  engine/stage2/   payment_progress · geotag_verification · cost_variance · timeline
  engine/          scoring.py · explain.py
  backtest/        CAG performance-audit replay cases
  seed/            synthetic data generator
  config/          weights.yaml — scoring weights, tunable without a code change
frontend/src/
  pages/district/  the one role built in depth
```

## Testing

```bash
cd backend && ./.venv/Scripts/pytest.exe
```

## Prototype status

The current build is a **UI prototype**: three of the six roles, on a placeholder
dataset compiled into the frontend. It runs with `npm run dev` alone — the
backend is not required.

| Screen | Role | State |
|---|---|---|
| Review queue | District Authority | Built |
| Work detail, findings, review workflow | District Authority | Built |
| District map | District Authority | Built |
| Trends | District Authority | Built |
| CAG backtest | District Authority | Built |
| My recommendations | Member of Parliament | Built |
| National overview | Ministry (MoSPI) | Built |
| State Nodal, Implementing Agency, Public | — | Named, not built |

The engine itself is not wired in yet: Phase 0 (scaffold) is complete on the
backend, and Phases 1–7 build the real Stage 1 and Stage 2 modules behind it.

`DESIGN.md` records the visual system and why each choice was made.
`DECISIONS.md` records every departure from the build specification.
