"""End-to-end: seed a corpus, score it, and check the engine found what was planted.

Marked slow because it generates and scores a full dataset. Run the fast suite
with ``pytest -m "not slow"``.

**What this measures, and what it does not.** Recall here is against anomalies
this project planted itself. A high number shows the detectors are wired to the
patterns they were built for and that a change has not silently broken one. It is
not a measurement of real-world detection accuracy, which would require
validation against live MPLADS records. The backtest screen carries the same
caveat in the words a juror will read.
"""

from __future__ import annotations

from collections import defaultdict

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.engine.context import financial_year_of
from app.models import Work
from app.models.risk import RiskFlag

pytestmark = pytest.mark.slow

# Enough works for the generator's floor of 30 instances per pattern to sit
# inside a realistic anomaly share rather than dominating the corpus.
CORPUS = 1500
MIN_RECALL = 0.75

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

# An entitlement breach belongs to a member's year and a quota shortfall to a
# district's year. The engine raises them against the works that caused them
# rather than against every work in the group, so per-work recall would measure
# the labelling convention instead of the detection.
GROUP_LEVEL = {
    "ENTITLEMENT_BREACH": ("mp_id", {"ENTITLEMENT_EXCEEDED"}),
    "QUOTA_SHORTFALL": ("district_id", {"QUOTA_SHORTFALL"}),
}


@pytest.fixture(scope="module")
def scored_corpus(tmp_path_factory):
    """Seed and score once; every assertion below reads the same result."""
    import random

    from app.engine import runner
    from app.seed import generate

    path = tmp_path_factory.mktemp("recall") / "corpus.db"
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, expire_on_commit=False)

    with maker() as db:
        rng = random.Random(42)
        ref = generate.seed_reference(db, rng)
        generate.seed_users(db, ref)
        generate.seed_engine_config(db)
        works = generate.build_works(db, rng, ref, CORPUS)
        generate.build_downstream(db, rng, works, ref)
        db.flush()
        targets = generate.target_counts(CORPUS)
        generate.plant_per_work(db, rng, works, targets)
        generate.plant_structural(db, rng, works, targets, ref)
        db.commit()

        runner.assess_all(db)

        flags = defaultdict(set)
        for work_id, code in db.execute(select(RiskFlag.work_id, RiskFlag.flag_code)):
            flags[work_id].add(code)
        rows = db.scalars(select(Work)).all()
        return {
            "flags": flags,
            "works": [
                {
                    "work_id": w.work_id,
                    "planted": w.planted_anomaly.value if w.planted_anomaly else None,
                    "mp_id": w.mp_id,
                    "district_id": w.district_id,
                    "recommended_date": w.recommended_date,
                }
                for w in rows
            ],
        }


def _planted(corpus, anomaly):
    return [w for w in corpus["works"] if w["planted"] == anomaly]


@pytest.mark.parametrize("anomaly", sorted(EXPECTED))
def test_per_work_recall_above_threshold(scored_corpus, anomaly):
    members = _planted(scored_corpus, anomaly)
    assert members, f"generator planted no {anomaly}; the answer key is empty"

    want = EXPECTED[anomaly]
    caught = sum(1 for w in members if scored_corpus["flags"].get(w["work_id"], set()) & want)
    recall = caught / len(members)
    assert recall >= MIN_RECALL, (
        f"{anomaly}: {caught}/{len(members)} = {recall:.0%}, below {MIN_RECALL:.0%}. "
        f"Expected any of {sorted(want)}."
    )


@pytest.mark.parametrize("anomaly", sorted(GROUP_LEVEL))
def test_group_level_recall_above_threshold(scored_corpus, anomaly):
    key_field, want = GROUP_LEVEL[anomaly]
    groups = defaultdict(list)
    for w in _planted(scored_corpus, anomaly):
        if w["recommended_date"]:
            groups[(w[key_field], financial_year_of(w["recommended_date"]))].append(w["work_id"])

    assert groups, f"generator planted no {anomaly} group"
    caught = sum(
        1
        for ids in groups.values()
        if any(scored_corpus["flags"].get(i, set()) & want for i in ids)
    )
    recall = caught / len(groups)
    assert recall >= MIN_RECALL, f"{anomaly}: {caught}/{len(groups)} groups = {recall:.0%}"


def test_false_positive_rate_stays_reasonable(scored_corpus):
    """A reviewer's time is the cost of a wrong flag, so the rate has to be liveable.

    Not zero: the agency signal fires for the bottom fifth of every peer group by
    construction, and it is context rather than an allegation.
    """
    clean = [w for w in scored_corpus["works"] if w["planted"] is None]
    flagged = sum(1 for w in clean if scored_corpus["flags"].get(w["work_id"]))
    rate = flagged / len(clean)
    assert rate < 0.15, f"{flagged}/{len(clean)} clean works flagged = {rate:.1%}"


def test_every_finding_carries_an_explanation(scored_corpus):
    """A finding with no readable reason is a bug, per design rule four."""
    from app.engine import explain

    for code in {c for codes in scored_corpus["flags"].values() for c in codes}:
        assert code in explain.TEMPLATES, f"{code} was raised with no explanation template"
