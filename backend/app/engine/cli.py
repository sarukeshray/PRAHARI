"""Engine command line.

    python -m app.engine.cli score     # assess every work, persist the results
    python -m app.engine.cli recall    # grade the engine against the answer key

``recall`` is the number to look at after any change to a module or a threshold.
It reports per-pattern recall against the planted anomalies and the share of
unplanted works that still drew a finding.
"""

from __future__ import annotations

import argparse
import logging
import time
from collections import defaultdict
from datetime import date

from sqlalchemy import select

from app.db import SessionLocal
from app.engine import runner
from app.engine.similarity import backend
from app.models import Work
from app.models.risk import RiskFlag

# Which flag codes count as catching which planted pattern.
EXPECTED = {
    "COST_INFLATION": {"COST_ABOVE_SOR", "COST_PEER_OUTLIER"},
    "DUPLICATE_WORK": {"DUPLICATE_CANDIDATE"},
    "SALAMI_SLICING": {"SPLIT_WORK_PATTERN"},
    "PAYMENT_AHEAD": {"PAYMENT_AHEAD_OF_PROGRESS", "FULLY_PAID_INCOMPLETE"},
    "GEOTAG_MISMATCH": {"PHOTO_LOCATION_MISMATCH"},
    "PHOTO_REUSE": {"PHOTO_REUSED_ACROSS_WORKS"},
    "TIMELINE_BREACH": {
        "COMPLETION_OVERDUE_12M",
        "PROGRESS_REPORTING_STALLED",
        "SANCTION_DELAY_45D",
    },
    "COST_OVERRUN": {"COST_OVERRUN"},
    "GHOST_WORK": {"GHOST_WORK", "NO_COMPLETION_EVIDENCE", "FULLY_PAID_INCOMPLETE"},
    "HANDOVER_GAP": {"HANDOVER_OVERDUE", "UC_MISSING"},
}

# Facts about a group rather than about a work, so scored per group.
GROUP_LEVEL = {
    "ENTITLEMENT_BREACH": ("mp_id", {"ENTITLEMENT_EXCEEDED"}),
    "QUOTA_SHORTFALL": ("district_id", {"QUOTA_SHORTFALL"}),
}


def financial_year_of(d: date) -> int:
    return d.year if d.month >= 4 else d.year - 1


def cmd_score() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    started = time.time()
    with SessionLocal() as db:
        summary = runner.assess_all(db)

    print(f"\n  similarity backend  {backend()}")
    print(f"  elapsed             {time.time() - started:.1f}s")
    print(f"  works scored        {summary['works']}")
    print(f"  assessments         {summary['assessments']}")
    print(f"  findings            {summary['findings']}")

    print("\n  assessments by tier")
    for tier in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        print(f"    {tier:10} {summary['by_tier'].get(tier, 0)}")

    print("\n  findings by code")
    for code, n in sorted(summary["by_code"].items(), key=lambda kv: -kv[1]):
        print(f"    {code:32} {n}")


def cmd_recall() -> None:
    with SessionLocal() as db:
        flags: dict[str, set[str]] = defaultdict(set)
        for work_id, code in db.execute(select(RiskFlag.work_id, RiskFlag.flag_code)):
            flags[work_id].add(code)
        works = db.scalars(select(Work)).all()

    planted: dict[str, list[Work]] = defaultdict(list)
    clean: list[Work] = []
    for w in works:
        (planted[w.planted_anomaly.value].append(w) if w.planted_anomaly else clean.append(w))

    print("\n  Method sensitivity on synthetic data")
    print("  Recall against anomalies this project planted itself. It shows the")
    print("  detectors are wired to the patterns they were built for. It is NOT a")
    print("  measurement of real-world accuracy.\n")
    print(f"  {'planted pattern':22} {'unit':>6} {'n':>5} {'caught':>7} {'recall':>8}  status")
    print(f"  {'-' * 22} {'-' * 6} {'-' * 5} {'-' * 7} {'-' * 8}  {'-' * 6}")

    failures = []
    for anomaly in sorted(planted):
        members = planted[anomaly]
        if anomaly in GROUP_LEVEL:
            key_field, want = GROUP_LEVEL[anomaly]
            groups: dict[tuple, list[str]] = defaultdict(list)
            for w in members:
                if w.recommended_date:
                    key = (getattr(w, key_field), financial_year_of(w.recommended_date))
                    groups[key].append(w.work_id)
            n = len(groups)
            caught = sum(1 for ids in groups.values() if any(flags.get(i, set()) & want for i in ids))
            unit = "group"
        else:
            want = EXPECTED.get(anomaly, set())
            n = len(members)
            caught = sum(1 for w in members if flags.get(w.work_id, set()) & want)
            unit = "work"

        recall = caught / n if n else 0.0
        status = "PASS" if recall >= 0.75 else ("weak" if recall >= 0.5 else "FAIL")
        if recall < 0.75:
            failures.append(anomaly)
        print(f"  {anomaly:22} {unit:>6} {n:>5} {caught:>7} {recall:>7.1%}  {status}")

    flagged_clean = sum(1 for w in clean if flags.get(w.work_id))
    rate = flagged_clean / len(clean) if clean else 0.0
    print(f"\n  works with no planted anomaly   {len(clean)}")
    print(f"  of those, drew a finding        {flagged_clean}  ({rate:.1%})")
    print(f"  patterns below 0.75 recall      {', '.join(failures) if failures else 'none'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="PRAHARI engine commands.")
    parser.add_argument("command", choices=["score", "recall"])
    args = parser.parse_args()
    {"score": cmd_score, "recall": cmd_recall}[args.command]()


if __name__ == "__main__":
    main()
