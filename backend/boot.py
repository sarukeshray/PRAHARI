"""Prepare the database, then hand over to the server.

Hosting platforms give a container an empty disk on every deploy. This makes the
first request work anyway: migrate, seed if there are no works, and score if
there are no assessments. Each step is skipped when it has already been done, so
a restart is fast and a redeploy is not.

    python boot.py && uvicorn app.main:app --host 0.0.0.0 --port $PORT
"""

from __future__ import annotations

import subprocess
import sys
import time

from sqlalchemy import func, select

from app.db import SessionLocal, engine
from app.models import Work
from app.models.risk import RiskAssessment


def run(label: str, args: list[str]) -> None:
    print(f"  {label} ...", flush=True)
    started = time.time()
    result = subprocess.run([sys.executable, *args], check=False)
    if result.returncode != 0:
        raise SystemExit(f"  FAILED: {label}")
    print(f"  {label} done in {time.time() - started:.0f}s", flush=True)


def main() -> None:
    print("PRAHARI boot", flush=True)

    # Through sys.executable, not the bare `alembic` command: on a machine with
    # more than one Python the bare command can resolve to an interpreter that
    # has none of this project's dependencies installed.
    run("applying migrations", ["-m", "alembic", "upgrade", "head"])

    with SessionLocal() as db:
        works = db.scalar(select(func.count()).select_from(Work)) or 0
        assessments = db.scalar(select(func.count()).select_from(RiskAssessment)) or 0

    if works == 0:
        run("seeding 4,000 works", ["-m", "app.seed.generate", "--works", "4000", "--seed", "42"])
    else:
        print(f"  {works:,} works already present, skipping seed", flush=True)

    if assessments == 0:
        run("scoring the corpus", ["-m", "app.engine.cli", "score"])
    else:
        print(f"  {assessments:,} assessments already present, skipping scoring", flush=True)

    from app.engine.similarity import backend

    print(f"  similarity backend: {backend()}", flush=True)
    print("  ready", flush=True)


if __name__ == "__main__":
    main()
