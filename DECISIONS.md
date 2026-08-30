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
