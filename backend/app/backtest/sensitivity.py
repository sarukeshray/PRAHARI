"""Method sensitivity — grade the engine against the planted answer key.

Computed live from the working corpus rather than pasted from a CLI run, so the
figure on the screen can never drift from the engine that produced it.

**What this measures.** Recall against anomalies this project planted itself. It
shows the detectors are wired to the patterns they were built for, and that a
change has not silently broken one. It is not real-world accuracy.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Work
from app.models.risk import RiskFlag

#: Which flag codes count as catching which planted pattern.
EXPECTED: dict[str, set[str]] = {
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

#: Facts about a group rather than a work. The engine raises these against the
#: works that caused them rather than every work in the group, so per-work recall
#: would measure the labelling convention instead of the detection.
GROUP_LEVEL: dict[str, tuple[str, set[str]]] = {
    "ENTITLEMENT_BREACH": ("mp_id", {"ENTITLEMENT_EXCEEDED"}),
    "QUOTA_SHORTFALL": ("district_id", {"QUOTA_SHORTFALL"}),
}


def _financial_year(d: date) -> int:
    return d.year if d.month >= 4 else d.year - 1


def compute_sensitivity(db: Session) -> dict:
    flags: dict[str, set[str]] = defaultdict(set)
    for work_id, code in db.execute(select(RiskFlag.work_id, RiskFlag.flag_code)):
        flags[work_id].add(code)

    works = db.scalars(select(Work)).all()
    planted: dict[str, list[Work]] = defaultdict(list)
    clean: list[Work] = []
    for w in works:
        if w.planted_anomaly:
            planted[w.planted_anomaly.value].append(w)
        else:
            clean.append(w)

    rows = []
    for anomaly in sorted(planted):
        members = planted[anomaly]

        if anomaly in GROUP_LEVEL:
            key_field, want = GROUP_LEVEL[anomaly]
            groups: dict[tuple, list[str]] = defaultdict(list)
            for w in members:
                if w.recommended_date:
                    groups[
                        (getattr(w, key_field), _financial_year(w.recommended_date))
                    ].append(w.work_id)
            total = len(groups)
            caught = sum(
                1 for ids in groups.values() if any(flags.get(i, set()) & want for i in ids)
            )
            unit = "group"
        else:
            want = EXPECTED.get(anomaly, set())
            total = len(members)
            caught = sum(1 for w in members if flags.get(w.work_id, set()) & want)
            unit = "work"

        rows.append(
            {
                "anomaly": anomaly,
                "unit": unit,
                "planted": total,
                "recalled": caught,
                "recall": round(caught / total, 4) if total else 0.0,
                "expected_flags": sorted(
                    GROUP_LEVEL[anomaly][1] if anomaly in GROUP_LEVEL else EXPECTED.get(anomaly, set())
                ),
            }
        )

    flagged_clean = sum(1 for w in clean if flags.get(w.work_id))

    # The agency signal fires for the weakest fifth of every peer group by
    # construction. Reporting the rate with and without it stops a structural
    # property being read as detector noise.
    flagged_clean_excl_agency = sum(
        1 for w in clean if flags.get(w.work_id, set()) - {"AGENCY_HISTORICAL_CONCERN"}
    )

    return {
        "patterns": rows,
        "clean_works": len(clean),
        "clean_works_flagged": flagged_clean,
        "clean_flag_rate": round(flagged_clean / len(clean), 4) if clean else 0.0,
        "clean_works_flagged_excluding_agency_signal": flagged_clean_excl_agency,
        "clean_flag_rate_excluding_agency_signal": (
            round(flagged_clean_excl_agency / len(clean), 4) if clean else 0.0
        ),
        "note": (
            "Recall is measured against anomalies this project planted itself. It shows the "
            "detectors are wired to the patterns they were built for and that a change has not "
            "silently broken one. It is not a measurement of real-world accuracy."
        ),
    }
