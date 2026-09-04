# Hosting PRAHARI and sharing a link

Two routes, for two different needs. Read §1 before choosing — the constraint
that decides it is not obvious.

| | Route A — tunnel | Route B — Render |
|---|---|---|
| Time | 5 minutes | 30–40 minutes |
| Cost | Free | ~$14/month (two paid services) |
| Link lives | While your laptop is on | Always |
| Duplicate detection | Full transformer | Character n-gram fallback |
| Best for | Showing teammates today | A link on a slide |

**If you only need teammates to see it, take Route A.** It is faster, free, and
runs the *exact* build you have been testing.

---

## 1. The constraint that decides everything

The backend imports `sentence-transformers`, which pulls in PyTorch: about **2.5
GB installed**, and it needs well over 512 MB of RAM to load the model. Every
free hosting tier is 512 MB. It will not fit, and it will not fail gracefully —
the container is killed mid-request.

So a hosted deployment installs `backend/requirements-deploy.txt` instead, which
omits PyTorch. The duplicate module detects this and falls back to character
n-gram similarity automatically, using its own calibrated threshold.

**What that actually costs you**, measured on the corpus rather than guessed:

| | Transformer | n-gram fallback |
|---|---|---|
| Planted duplicates caught | 40/40 | 20/20 (sampled) |
| Clean works wrongly flagged | ~0 | 1 in 120 |
| Catches a *reworded* duplicate | Yes | Weaker — it matches text, not meaning |

Everything else — Isolation Forest, all ten modules, scoring, explanations,
EXIF extraction, the backtest — is unaffected. `GET /api/v1/engine/weights`
reports which backend is live, so it is never ambiguous which one a demo ran on.

> **For a jury**, prefer Route A. "The real transformer is running" is a stronger
> claim, and it costs nothing.

---

## Route A — share your local machine (5 minutes, free)

A tunnel gives your laptop a public HTTPS address. Teammates open a normal link;
everything runs on your machine, exactly as you have been testing it.

### Step 1 — install cloudflared

```powershell
winget install --id Cloudflare.cloudflared
```

No account needed for a quick tunnel.

### Step 2 — start both servers as usual

```powershell
# Terminal 1
cd "C:\Users\saruk\Desktop\Sarukesh\SIH 2026\Project\prahari\backend"
.\.venv\Scripts\uvicorn.exe app.main:app --port 8001
```

```powershell
# Terminal 2
cd "C:\Users\saruk\Desktop\Sarukesh\SIH 2026\Project\prahari\frontend"
npm run dev -- --host
```

The `--host` matters: without it Vite binds to localhost only and the tunnel
reaches nothing.

### Step 3 — open the tunnel

```powershell
# Terminal 3
cloudflared tunnel --url http://localhost:5173
```

It prints something like:

```
Your quick Tunnel has been created! Visit it at:
https://spare-mineral-fabric-tone.trycloudflare.com
```

**That is the link.** Send it to your teammates.

### Step 4 — allow the tunnel host through Vite

Vite blocks unknown hostnames. Add this to `frontend/vite.config.ts` inside
`server`, then restart the dev server:

```ts
server: {
  port: 5173,
  allowedHosts: ['.trycloudflare.com'],
  proxy: { '/api': { target: 'http://127.0.0.1:8001', changeOrigin: true } },
},
```

The `/api` proxy already exists, so the backend needs no tunnel of its own —
requests go through the frontend and out to `:8001` locally.

### Things to know

- The link dies when you close the terminal or the laptop sleeps. **Disable
  sleep before a demo.**
- A quick tunnel gets a new random URL each time. For a stable address you need
  a free Cloudflare account and a named tunnel.
- Anyone with the link can reach it. There is no password — the sign-in is demo
  mode. Do not post it publicly.

---

## Route B — Render (30–40 minutes, ~$14/month)

Two services: a Docker backend and a static frontend. Everything needed is
already committed — `backend/Dockerfile`, `backend/boot.py`,
`backend/requirements-deploy.txt`, and `render.yaml`.

### Step 1 — push, and check the branch

```powershell
cd "C:\Users\saruk\Desktop\Sarukesh\SIH 2026\Project\prahari"
git push origin MVP
```

Render deploys a branch you choose. This project's work is on **`MVP`**, not
`main` — select it explicitly at every step below, or you will deploy the old
UI-only prototype.

### Step 2 — create the two services

1. Go to **dashboard.render.com** → **New** → **Blueprint**
2. Connect the `sarukeshray/PRAHARI` repository
3. **Set the branch to `MVP`**
4. Render reads `render.yaml` and offers two services: `prahari-api` and
   `prahari`. Approve both.

The first backend build takes 5–8 minutes. It then runs `boot.py`, which seeds
4,000 works and scores them — **another 2–4 minutes**. The service reports
unhealthy until that finishes. This is expected on the first deploy only.

### Step 3 — introduce the two services to each other

Neither URL exists until the first deploy, so this cannot be in the blueprint.

Once both are live, note the two addresses (yours will differ):

```
API       https://prahari-api.onrender.com
Frontend  https://prahari.onrender.com
```

Then:

1. **`prahari-api` → Environment** → set `CORS_ORIGINS` to your frontend URL,
   e.g. `https://prahari.onrender.com` — **no trailing slash**
2. **`prahari` → Environment** → set `VITE_API_BASE_URL` to your API URL,
   e.g. `https://prahari-api.onrender.com` — **no trailing slash**
3. Redeploy the frontend. `VITE_` variables are baked in at build time, so an
   environment change does nothing until it rebuilds.

### Step 4 — check it

```powershell
curl.exe https://prahari-api.onrender.com/api/v1/health
```

Expect:

```json
{"status":"ok","engine_version":"1.0.0","db_backend":"sqlite",
 "auth":"demo","works_loaded":4000, ...}
```

`works_loaded: 0` means `boot.py` has not finished. Watch the service logs.

Then open the frontend URL and sign in as District Authority.

### Why the paid plan

`render.yaml` specifies `plan: starter` (~$7/service/month) for a reason: the
free tier spins down after 15 minutes of inactivity, and a cold start re-runs
`boot.py` — so the first visitor after a quiet hour waits several minutes and
probably assumes it is broken. For a link on a slide, that is worse than not
having one.

The **disk** in `render.yaml` also matters. Without it the SQLite file and every
uploaded photograph are wiped on each redeploy.

---

## After deploying, check these six things

Route B changes the environment enough that these are worth confirming. All six
work locally; the first three are the ones a misconfiguration breaks.

| # | Check | Where |
|---|---|---|
| 1 | Sign-in works and each role lands on its own dashboard | `/signin` |
| 2 | Review queue loads with real counts | District Authority |
| 3 | The findings PDF downloads | District Authority → Findings PDF |
| 4 | The backtest computes | District Authority → CAG backtest → Run |
| 5 | A photograph uploads and EXIF is read | Implementing Agency → My works → Update |
| 6 | The public form accepts a submission | `/public`, no sign-in |

**If 1 fails with "Bad Gateway" or a CORS error**, the two URLs are not
introduced to each other. Re-check step 3, watch for trailing slashes, and
confirm the frontend was rebuilt after `VITE_API_BASE_URL` was set.

**If 4 times out**, the backend is on the free plan and ran out of memory.

---

## What your teammates will see

Everything works without any setup on their side. They open the link, pick a
role, and sign in — no password.

| Role | Sees |
|---|---|
| District Authority | Review queue, work detail with the review workflow, map, trends, handover queue, citizen submissions, CAG backtest |
| Member of Parliament | Entitlement tracker, own works, submit a recommendation |
| Ministry | National overview, fund-flow Sankey, state map, threshold configuration |
| State Nodal | State overview, escalation queue, reassignment |
| Implementing Agency | Assigned works, progress reports, photo upload, respond to findings |
| User Agency | Assets handed over, acknowledge, check-ins, maintenance |
| Public | Aggregates only — and deliberately nothing else |

Two things to tell them so they are not misled:

- **The sign-in does not check a password.** Firebase is not configured. The
  *authorisation* behind it is real: each role genuinely cannot see the others'
  data, and 43 tests prove it.
- **All data is synthetic**, which the badge on every screen says.

---

## Cheaper and other options

**Railway** — same Docker image, usage-based pricing, roughly $5/month at this
size. Point it at `backend/Dockerfile` and deploy the frontend separately on
Vercel or Cloudflare Pages (both free for static).

**Fly.io** — has a free allowance that may cover this. Needs `fly launch` in
`backend/` and a `fly.toml`; a volume is required for the same reason as
Render's disk.

**Frontend anywhere, backend on Render** — Vercel, Netlify and Cloudflare Pages
all host the static build for free. Build command `npm run build`, output
directory `dist`, and set `VITE_API_BASE_URL`. Add a rewrite so every path
serves `index.html`, or deep links 404.

**Do not** deploy the backend to Vercel or Netlify. Both are serverless and cap
execution well below what scoring 4,000 works needs.

---

## Before you share the link publicly

The demo is safe to share with teammates. Before it goes anywhere wider:

- **The sign-in accepts any role with no password.** Anyone with the link is a
  Ministry user if they choose to be.
- **`POST /public/submissions` is unauthenticated and unthrottled.** Length caps
  bound one request; nothing bounds a flood.
- **Photograph upload writes to disk** with a 10 MB cap and no total quota.

None of these matter for a private link. All three need addressing before
anything public. They are recorded in `docs/STATUS_REPORT.md` §4.
