# External setup

Everything you need to do outside the editor. Firebase has its own file —
`docs/FIREBASE_SETUP.md` — which lands at the start of Phase 3.

Nothing in this document is required to run the project today. The generator
synthesises its own Schedule of Rates and cost index, so `python -m app.seed.generate`
works on a clean checkout with no downloads. Each section below tells you what
improves if you supply the real data, and exactly where to put it.

---

## 1. Run it locally (required, 5 minutes)

Assumes Python 3.11+ and Node 20+ are already installed.

```powershell
# Backend
cd "C:\Users\saruk\Desktop\Sarukesh\SIH 2026\Project\prahari\backend"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\python.exe -m app.seed.generate --works 4000 --seed 42 --reset
.\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8001
```

```powershell
# Frontend, in a second terminal
cd "C:\Users\saruk\Desktop\Sarukesh\SIH 2026\Project\prahari\frontend"
npm install
npm run dev
```

The seed step prints a summary. Sanity-check it against this:

```
works                4000
planted anomalies     560   (14.0% of works)
RECOMMENDED           751     <- the population Stage 1 screens
```

The same `--seed` always produces the same dataset. Re-run with `--reset` any
time you want a clean slate; leave the seed at 42 so screenshots and the
sensitivity numbers stay consistent between rehearsal and the actual demo.

**Database.** SQLite by default, no container runtime needed. For PostgreSQL +
PostGIS: `docker compose up -d`, then set `DB_BACKEND=postgres` in `backend/.env`.

---

## 2. Environment variables

Copy `backend/.env.example` to `backend/.env` and edit. The file today:

| Variable | Default | What it does |
|---|---|---|
| `DB_BACKEND` | `sqlite` | `sqlite` or `postgres` |
| `POSTGRES_URL` | localhost | Only read when `DB_BACKEND=postgres` |
| `ENGINE_VERSION` | `0.1.0` | Stamped on every assessment for traceability |

Firebase variables get added to this file in Phase 3; `FIREBASE_SETUP.md` will
name each one.

**Never commit `backend/.env`.** It is already in `.gitignore`. The same goes for
the Firebase service-account JSON when it arrives.

---

## 3. State Schedule of Rates — optional, improves credibility

**What it changes.** Right now the generator invents SoR rates: a plausible base
rate per work type, escalated 6.2% a year, multiplied by a terrain factor. The
cost module works correctly against these. Supplying real rates means a juror who
asks *"where does ₹12,90,000 come from?"* gets "the Rajasthan PWD Schedule of
Rates, 2025, page 47" instead of "a synthetic benchmark".

**Where to get it.** Each state PWD publishes its SoR annually as a PDF or Excel
workbook — search `"<state> PWD Schedule of Rates <year>"`. Start with Rajasthan
and Kerala, which two of the three seeded states use.

**Where to put it.** Create `backend/data/sor/` and drop one CSV per state:

```
backend/data/sor/rajasthan_2025.csv
backend/data/sor/kerala_2025.csv
```

**Required columns**, exactly these headers:

```csv
work_type,unit,unit_rate,terrain_category,year
ROAD_CC,per km,4180000,PLAIN,2025
ROAD_CC,per km,5350000,HILLY,2025
COMMUNITY_HALL,per unit,1840000,PLAIN,2025
```

`work_type` must be one of the twelve codes in
`backend/app/seed/catalog.py` → `WORK_TYPES`. `terrain_category` must be one of
`PLAIN`, `HILLY`, `REMOTE`, `COASTAL`, `URBAN`.

The loader that reads this directory lands in Phase 2. Until then the files are
ignored, so you can prepare them at any point without breaking anything.

---

## 4. Construction cost index — optional, for the real-terms view only

**What it changes.** One chart on the District Trends screen, showing cost
movement in constant rupees. **The engine does not use it.** Flagging compares a
work against the Schedule of Rates *for its own year*, which cancels inflation
out of the comparison arithmetically — no deflator required. This file exists so
that when a juror asks how inflation is handled, you can show the real-terms
series as well as explain the ratio.

**Where to get it.** CPWD publishes a Cost Index; the Office of the Economic
Adviser publishes the WPI series for construction materials at
eaindustry.nic.in. Either works — pick one and stay with it.

**Where to put it.** `backend/data/cost_index.csv`:

```csv
year,index_value,source
2023,100.0,CPWD
2024,106.4,CPWD
2025,113.1,CPWD
2026,120.2,CPWD
```

If the file is absent the chart hides itself rather than showing invented
numbers.

---

## 5. CAG reports — recommended, this is the credibility anchor

**What it changes.** The backtest screen replays patterns from real CAG audit
findings. The case text is already encoded from published figures, but having the
source PDFs to hand means you can answer "which report, which paragraph?" in Q&A.

**What to fetch**, from cag.gov.in:

- **Report No. 31 of 2010** — Performance Audit of MPLADS. This is the primary
  source: the ₹53.74 crore inadmissible-works figure, the 775 never-taken-up
  works, the 568 delayed works, and the 558 works executed without
  recommendation all come from here.
- Any later MPLADS compliance report for your state, for a more recent citation.

**Where to put it.** `docs/references/` — PDFs are gitignored, so they stay on
your machine:

```
docs/references/cag_report_31_2010_mplads.pdf
```

Note the paragraph number next to each figure as you find it. Five citations is
enough, and it is the single highest-value hour of preparation for the Q&A round.

---

## 6. Google Colab — Phase 7

`notebooks/prahari_model_training.ipynb` does not exist yet. When it does:

1. Open colab.research.google.com → File → Upload notebook → pick the file
2. Runtime → Run all. It generates its own data, so nothing needs uploading
   alongside it
3. The last cell writes `isolation_forest.joblib` — download it via the file
   browser in Colab's left sidebar
4. Put it at `backend/app/engine/artifacts/isolation_forest.joblib`

The backend falls back to fitting the model in-process if that file is missing,
so the notebook is evidence of real training rather than a hard dependency.

---

## 7. Deployment

Local only for this round, by decision. Both servers run on your laptop for the
demo — no venue wifi dependency, no cold starts.

If that changes, the shape is: frontend to Vercel, FastAPI plus Postgres to
Render. Flagged as a Phase 7 decision in `DECISIONS.md`.

---

## Checklist

| Task | Needed for | Status |
|---|---|---|
| Run backend + frontend locally | Everything | Required |
| `backend/.env` from the example | Everything | Required |
| Firebase project | Phase 3 onward | Blocks login and photo upload |
| State SoR CSVs | Credibility of cost flags | Optional |
| Cost index CSV | One Trends chart | Optional |
| CAG report PDFs | Q&A defence | Strongly recommended |
| Colab notebook run | Phase 7 evidence | Later |
