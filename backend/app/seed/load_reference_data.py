"""Load real Schedule of Rates and cost-index data, if it has been supplied.

    python -m app.seed.load_reference_data

The generator synthesises rates so the project runs on a clean checkout with no
downloads. This replaces those synthetic rates with published ones where a state
file exists, which changes what a cost finding can cite: "the Rajasthan Schedule
of Rates, 2025" rather than "a synthetic benchmark".

Both inputs are optional and independent. A missing file is reported and skipped,
never an error — the point of this script is to improve provenance where the data
exists, not to become a dependency.

File locations and the exact column headers are documented in
``docs/EXTERNAL_SETUP.md``.
"""

from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy import delete, select

from app.config.settings import BACKEND_ROOT
from app.db import SessionLocal
from app.models import CostIndex, SORBenchmark
from app.models.enums import Terrain

SOR_DIR = BACKEND_ROOT / "data" / "sor"
COST_INDEX_FILE = BACKEND_ROOT / "data" / "cost_index.csv"

SOR_COLUMNS = {"work_type", "unit", "unit_rate", "terrain_category", "year"}
INDEX_COLUMNS = {"year", "index_value"}

VALID_TERRAIN = {t.value for t in Terrain}


def _state_from_filename(path: Path) -> str:
    """`rajasthan_2025.csv` -> `Rajasthan`."""
    stem = path.stem.rsplit("_", 1)[0]
    return " ".join(part.capitalize() for part in stem.split("_"))


def load_sor(db, path: Path) -> tuple[int, list[str]]:
    """Load one state's rates. Returns (rows loaded, problems found)."""
    state = _state_from_filename(path)
    problems: list[str] = []

    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        headers = set(reader.fieldnames or [])
        missing = SOR_COLUMNS - headers
        if missing:
            return 0, [f"{path.name}: missing columns {sorted(missing)}"]

        rows = list(reader)

    loaded = 0
    for n, row in enumerate(rows, start=2):
        terrain = (row["terrain_category"] or "").strip().upper()
        if terrain not in VALID_TERRAIN:
            problems.append(f"{path.name} line {n}: terrain {terrain!r} is not one of {sorted(VALID_TERRAIN)}")
            continue
        try:
            year = int(row["year"])
            rate = float(row["unit_rate"])
        except (TypeError, ValueError):
            problems.append(f"{path.name} line {n}: year or unit_rate is not a number")
            continue
        if rate <= 0:
            problems.append(f"{path.name} line {n}: unit_rate must be positive")
            continue

        work_type = (row["work_type"] or "").strip().upper()

        # Replace rather than duplicate, so re-running is safe.
        existing = db.scalar(
            select(SORBenchmark).where(
                SORBenchmark.state == state,
                SORBenchmark.work_type == work_type,
                SORBenchmark.year == year,
                SORBenchmark.terrain_category == Terrain(terrain),
            )
        )
        if existing:
            existing.unit_rate = rate
            existing.unit = (row["unit"] or existing.unit).strip()
        else:
            db.add(
                SORBenchmark(
                    state=state,
                    work_type=work_type,
                    unit=(row["unit"] or "per unit").strip(),
                    unit_rate=rate,
                    year=year,
                    terrain_category=Terrain(terrain),
                    terrain_multiplier=1.0,
                )
            )
        loaded += 1

    return loaded, problems


def load_cost_index(db, path: Path) -> tuple[int, list[str]]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = INDEX_COLUMNS - set(reader.fieldnames or [])
        if missing:
            return 0, [f"{path.name}: missing columns {sorted(missing)}"]
        rows = list(reader)

    db.execute(delete(CostIndex))
    loaded = 0
    problems: list[str] = []
    for n, row in enumerate(rows, start=2):
        try:
            year = int(row["year"])
            value = float(row["index_value"])
        except (TypeError, ValueError):
            problems.append(f"{path.name} line {n}: year or index_value is not a number")
            continue
        db.add(CostIndex(year=year, index_value=value, source=(row.get("source") or "CPWD").strip()))
        loaded += 1
    return loaded, problems


def main() -> None:
    print("  Loading published reference data, where it has been supplied.\n")
    any_loaded = False

    with SessionLocal() as db:
        # --- Schedule of Rates ---
        if not SOR_DIR.exists():
            print(f"  Schedule of Rates : no directory at {SOR_DIR.relative_to(BACKEND_ROOT)}")
            print("                      Synthetic rates remain in use. See docs/EXTERNAL_SETUP.md §3.")
        else:
            files = sorted(SOR_DIR.glob("*.csv"))
            if not files:
                print(f"  Schedule of Rates : no CSV files in {SOR_DIR.relative_to(BACKEND_ROOT)}")
            for path in files:
                loaded, problems = load_sor(db, path)
                state = _state_from_filename(path)
                print(f"  Schedule of Rates : {path.name} -> {loaded} rates for {state}")
                for problem in problems[:10]:
                    print(f"                      ! {problem}")
                if len(problems) > 10:
                    print(f"                      ! and {len(problems) - 10} more")
                any_loaded = any_loaded or loaded > 0

        # --- Cost index ---
        if not COST_INDEX_FILE.exists():
            print(f"\n  Cost index        : no file at {COST_INDEX_FILE.relative_to(BACKEND_ROOT)}")
            print("                      The real-terms chart stays hidden rather than inventing a series.")
        else:
            loaded, problems = load_cost_index(db, COST_INDEX_FILE)
            print(f"\n  Cost index        : {loaded} years loaded")
            for problem in problems[:10]:
                print(f"                      ! {problem}")
            any_loaded = any_loaded or loaded > 0

        db.commit()

    if any_loaded:
        print("\n  Done. Re-run scoring so findings cite the new rates:")
        print("    python -m app.engine.cli score")
    else:
        print("\n  Nothing loaded. The project runs correctly on synthetic rates;")
        print("  this step only improves what a cost finding can cite.")


if __name__ == "__main__":
    main()
