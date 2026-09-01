"""Per-module tests against fixtures with hand-checkable values.

Each test states the number it expects and why, so a failure identifies the
module rather than sending someone into the generator.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.engine import explain
from app.engine.scoring import score
from app.engine.stage1 import agency_performance, compliance_rules, cost_benchmark
from app.engine.stage1 import duplicate_detection
from app.engine.stage2 import cost_variance, geotag_verification, payment_progress, timeline
from app.engine.stage3 import handover
from app.models.enums import ModuleCode, SeverityTier, Stage, WorkStatus
from tests.conftest import (
    BENCHMARK,
    TODAY,
    add_handover,
    add_payment,
    add_photo,
    add_progress,
    ctx_for,
    make_work,
)


def codes(result) -> set[str]:
    return {f.code for f in result.findings}


# ---------------------------------------------------------------------------
# COST
# ---------------------------------------------------------------------------


def test_cost_on_benchmark_raises_nothing(db):
    work = make_work(db, "W-1", cost=BENCHMARK)
    assert codes(cost_benchmark.evaluate(work, ctx_for(db))) == set()


def test_cost_just_under_threshold_is_silent(db):
    # +24% against a +25% threshold. The boundary must not be leaky.
    work = make_work(db, "W-1", cost=BENCHMARK * 1.24)
    assert "COST_ABOVE_SOR" not in codes(cost_benchmark.evaluate(work, ctx_for(db)))


def test_cost_above_threshold_flags_with_correct_numbers(db):
    work = make_work(db, "W-1", cost=BENCHMARK * 1.41)
    result = cost_benchmark.evaluate(work, ctx_for(db))
    assert "COST_ABOVE_SOR" in codes(result)

    finding = next(f for f in result.findings if f.code == "COST_ABOVE_SOR")
    assert finding.signal_value == pytest.approx(41.0, abs=0.5)
    assert finding.threshold_value == 25.0

    sentence = explain.render(finding.code, finding.params)
    # The explanation must carry both numbers a reviewer would check.
    assert "41%" in sentence
    assert "Rs 14,10,000" in sentence
    assert "Rs 10,00,000" in sentence


def test_cost_far_below_benchmark_flags_as_scoping_concern(db):
    work = make_work(db, "W-1", cost=BENCHMARK * 0.60)
    result = cost_benchmark.evaluate(work, ctx_for(db))
    assert "COST_BELOW_SOR" in codes(result)


def test_uniform_inflation_raises_no_new_cost_flags(db):
    """The inflation defence, asserted directly.

    Two works identical in every respect except the year, each priced at exactly
    its own year's benchmark. Rates escalate 6% a year between them. Neither may
    flag: the ratio is what is measured, and the ratio has not moved.
    """
    old = make_work(db, "W-2023", cost=880_000.0, recommended=date(2023, 6, 1))
    new = make_work(db, "W-2026", cost=1_062_000.0, recommended=date(2026, 6, 1))
    ctx = ctx_for(db)

    assert new.estimated_cost / old.estimated_cost == pytest.approx(1.207, abs=0.01)
    assert codes(cost_benchmark.evaluate(old, ctx)) == set()
    assert codes(cost_benchmark.evaluate(new, ctx)) == set()


def test_district_wide_price_rise_raises_no_flags(db):
    """A uniform rise applied to every work of a type must produce no findings.

    This is the scenario the fairness argument rests on: costs went up for
    everyone, nobody did anything wrong, and the engine must stay quiet.
    """
    ctx = ctx_for(db)
    for i in range(12):
        work = make_work(db, f"W-{i}", cost=1_062_000.0, recommended=date(2026, 6, 1))
        assert codes(cost_benchmark.evaluate(work, ctx_for(db))) == set(), (
            f"work {i} flagged despite sitting exactly on its own year's benchmark"
        )


# ---------------------------------------------------------------------------
# DUPLICATE
# ---------------------------------------------------------------------------


def test_identical_description_nearby_and_recent_is_flagged(db):
    text = "Construction of cement concrete road with side drains at Testville village."
    make_work(db, "W-1", description=text, recommended=date(2025, 6, 1))
    copy = make_work(
        db, "W-2", description=text, recommended=date(2025, 8, 1), lat=20.001, lon=78.0
    )
    assert "DUPLICATE_CANDIDATE" in codes(duplicate_detection.evaluate(copy, ctx_for(db)))


def test_identical_description_far_away_is_not_flagged(db):
    """Similarity alone must never be enough - most works are described alike."""
    text = "Construction of cement concrete road with side drains at Testville village."
    make_work(db, "W-1", description=text, recommended=date(2025, 6, 1))
    far = make_work(db, "W-2", description=text, recommended=date(2025, 8, 1), lat=20.2, lon=78.2)
    assert "DUPLICATE_CANDIDATE" not in codes(duplicate_detection.evaluate(far, ctx_for(db)))


def test_identical_description_years_apart_is_not_flagged(db):
    text = "Construction of cement concrete road with side drains at Testville village."
    make_work(db, "W-1", description=text, recommended=date(2023, 1, 1))
    later = make_work(
        db, "W-2", description=text, recommended=date(2026, 6, 1), lat=20.001, lon=78.0
    )
    assert "DUPLICATE_CANDIDATE" not in codes(duplicate_detection.evaluate(later, ctx_for(db)))


def test_split_work_pattern_detected(db):
    """Four works, one agency, one small area, one window, each just under 5 lakh."""
    for i in range(4):
        make_work(
            db,
            f"W-{i}",
            cost=470_000 + i * 5_000,
            recommended=date(2025, 6, 1) + timedelta(days=i * 20),
            lat=20.0 + i * 0.0005,
            lon=78.0,
            description=f"Construction of pucca drainage line at Testville, segment {i + 1}.",
        )
    from app.models.works import Work

    work = db.get(Work, "W-0")
    assert "SPLIT_WORK_PATTERN" in codes(duplicate_detection.evaluate(work, ctx_for(db)))


def test_works_spread_wide_are_not_a_split(db):
    for i in range(4):
        make_work(
            db,
            f"W-{i}",
            cost=470_000,
            recommended=date(2025, 6, 1) + timedelta(days=i * 20),
            lat=20.0 + i * 0.05,  # kilometres apart
            lon=78.0,
        )
    from app.models.works import Work

    work = db.get(Work, "W-0")
    assert "SPLIT_WORK_PATTERN" not in codes(duplicate_detection.evaluate(work, ctx_for(db)))


# ---------------------------------------------------------------------------
# COMPLIANCE
# ---------------------------------------------------------------------------


def test_impermissible_work_type_flagged(db):
    work = make_work(db, "W-1", work_type="MEMORIAL_STATUE")
    assert "WORK_TYPE_NOT_PERMISSIBLE" in codes(compliance_rules.evaluate(work, ctx_for(db)))


def test_sanction_within_45_days_is_silent(db):
    work = make_work(
        db, "W-1", recommended=date(2025, 6, 1), sanctioned=date(2025, 7, 10),
        status=WorkStatus.SANCTIONED,
    )
    assert "SANCTION_DELAY_45D" not in codes(compliance_rules.evaluate(work, ctx_for(db)))


def test_sanction_taken_late_is_flagged(db):
    """A decision taken 90 days late is a breach even though it was taken."""
    work = make_work(
        db, "W-1", recommended=date(2025, 6, 1), sanctioned=date(2025, 8, 30),
        status=WorkStatus.SANCTIONED,
    )
    assert "SANCTION_DELAY_45D" in codes(compliance_rules.evaluate(work, ctx_for(db)))


def test_pending_decision_past_45_days_is_flagged(db):
    work = make_work(db, "W-1", recommended=TODAY - timedelta(days=60))
    result = compliance_rules.evaluate(work, ctx_for(db))
    assert "SANCTION_DELAY_45D" in codes(result)
    finding = next(f for f in result.findings if f.code == "SANCTION_DELAY_45D")
    assert "no sanction decision has been recorded" in explain.render(
        finding.code, finding.params
    )


def test_sanction_without_recommendation_flagged(db):
    work = make_work(
        db, "W-1", recommended=None, sanctioned=date(2025, 7, 1), status=WorkStatus.SANCTIONED
    )
    work.recommended_date = None
    db.flush()
    assert "MISSING_RECOMMENDATION" in codes(compliance_rules.evaluate(work, ctx_for(db)))


# ---------------------------------------------------------------------------
# AGENCY
# ---------------------------------------------------------------------------


def test_agency_not_flagged_on_thin_history(db):
    """Never a finding on a handful of works, however poor the record looks."""
    for i in range(4):
        make_work(
            db, f"W-{i}", status=WorkStatus.COMPLETED,
            sanctioned=date(2024, 1, 1), completed=date(2025, 11, 1),
            final_cost=BENCHMARK * 1.8,
        )
    from app.models.works import Work

    work = db.get(Work, "W-0")
    assert codes(agency_performance.evaluate(work, ctx_for(db))) == set()


# ---------------------------------------------------------------------------
# DISBURSEMENT
# ---------------------------------------------------------------------------


def test_payment_ahead_of_progress(db):
    work = make_work(
        db, "W-1", status=WorkStatus.IN_PROGRESS, sanctioned=date(2025, 7, 1)
    )
    add_progress(db, work, 30.0)
    add_payment(db, work, 85.0, progress=30.0)

    result = payment_progress.evaluate(work, ctx_for(db))
    assert "PAYMENT_AHEAD_OF_PROGRESS" in codes(result)
    finding = next(f for f in result.findings if f.code == "PAYMENT_AHEAD_OF_PROGRESS")
    assert finding.signal_value == pytest.approx(55.0, abs=0.5)


def test_payment_tracking_progress_is_silent(db):
    work = make_work(db, "W-1", status=WorkStatus.IN_PROGRESS, sanctioned=date(2025, 7, 1))
    add_progress(db, work, 60.0)
    add_payment(db, work, 65.0, progress=60.0)
    assert codes(payment_progress.evaluate(work, ctx_for(db))) == set()


# ---------------------------------------------------------------------------
# GEOTAG
# ---------------------------------------------------------------------------


def test_photo_at_site_is_silent(db):
    work = make_work(db, "W-1", status=WorkStatus.COMPLETED, sanctioned=date(2025, 1, 1))
    add_photo(db, work, captured=date(2025, 6, 1))
    assert "PHOTO_LOCATION_MISMATCH" not in codes(geotag_verification.evaluate(work, ctx_for(db)))


def test_photo_kilometres_away_is_flagged(db):
    work = make_work(db, "W-1", status=WorkStatus.COMPLETED, sanctioned=date(2025, 1, 1))
    add_photo(db, work, lat=20.05, lon=78.0, captured=date(2025, 6, 1))  # ~5.5 km
    result = geotag_verification.evaluate(work, ctx_for(db))
    assert "PHOTO_LOCATION_MISMATCH" in codes(result)
    finding = next(f for f in result.findings if f.code == "PHOTO_LOCATION_MISMATCH")
    assert finding.signal_value > 5000


def test_photo_predating_sanction_is_flagged(db):
    work = make_work(db, "W-1", status=WorkStatus.COMPLETED, sanctioned=date(2025, 6, 1))
    add_photo(db, work, captured=date(2025, 4, 1))
    assert "PHOTO_TIMESTAMP_INVALID" in codes(geotag_verification.evaluate(work, ctx_for(db)))


def test_same_photo_on_two_works_flags_both(db):
    a = make_work(db, "W-1", status=WorkStatus.COMPLETED, sanctioned=date(2025, 1, 1))
    b = make_work(db, "W-2", status=WorkStatus.COMPLETED, sanctioned=date(2025, 1, 1))
    add_photo(db, a, image_hash="shared", captured=date(2025, 6, 1))
    add_photo(db, b, image_hash="shared", captured=date(2025, 6, 1))
    ctx = ctx_for(db)
    assert "PHOTO_REUSED_ACROSS_WORKS" in codes(geotag_verification.evaluate(a, ctx))
    assert "PHOTO_REUSED_ACROSS_WORKS" in codes(geotag_verification.evaluate(b, ctx))


# ---------------------------------------------------------------------------
# VARIANCE
# ---------------------------------------------------------------------------


def test_overrun_under_threshold_silent(db):
    work = make_work(
        db, "W-1", status=WorkStatus.COMPLETED, sanctioned=date(2024, 6, 1),
        completed=date(2025, 5, 1), final_cost=BENCHMARK * 1.10,
    )
    assert codes(cost_variance.evaluate(work, ctx_for(db))) == set()


def test_overrun_above_threshold_flagged(db):
    work = make_work(
        db, "W-1", status=WorkStatus.COMPLETED, sanctioned=date(2024, 6, 1),
        completed=date(2025, 5, 1), final_cost=BENCHMARK * 1.30,
    )
    result = cost_variance.evaluate(work, ctx_for(db))
    assert "COST_OVERRUN" in codes(result)
    assert result.findings[0].signal_value == pytest.approx(30.0, abs=0.1)


# ---------------------------------------------------------------------------
# TIMELINE
# ---------------------------------------------------------------------------


def test_ghost_work_detected(db):
    """Fully paid, marked complete, no reports and no photographs."""
    work = make_work(
        db, "W-1", status=WorkStatus.COMPLETED, sanctioned=date(2024, 6, 1),
        completed=date(2025, 4, 1), final_cost=BENCHMARK,
    )
    add_payment(db, work, 100.0, progress=100.0)
    assert "GHOST_WORK" in codes(timeline.evaluate(work, ctx_for(db)))


def test_completed_work_with_reports_but_no_photo(db):
    work = make_work(
        db, "W-1", status=WorkStatus.COMPLETED, sanctioned=date(2024, 6, 1),
        completed=date(2025, 4, 1),
    )
    add_progress(db, work, 100.0)
    add_payment(db, work, 100.0, progress=100.0)
    assert "NO_COMPLETION_EVIDENCE" in codes(timeline.evaluate(work, ctx_for(db)))


def test_overdue_beyond_twelve_months(db):
    work = make_work(
        db, "W-1", status=WorkStatus.IN_PROGRESS, sanctioned=TODAY - timedelta(days=500)
    )
    add_progress(db, work, 60.0)
    assert "COMPLETION_OVERDUE_12M" in codes(timeline.evaluate(work, ctx_for(db)))


# ---------------------------------------------------------------------------
# HANDOVER (Stage 3)
# ---------------------------------------------------------------------------


def test_handover_inside_30_days_is_silent(db):
    work = make_work(
        db, "W-1", status=WorkStatus.COMPLETED, sanctioned=date(2025, 1, 1),
        completed=TODAY - timedelta(days=20),
    )
    add_handover(
        db, work, initiated=TODAY - timedelta(days=15),
        acknowledged=TODAY - timedelta(days=10),
        uc=TODAY - timedelta(days=12), register=TODAY - timedelta(days=8),
    )
    assert codes(handover.evaluate(work, ctx_for(db))) == set()


@pytest.mark.parametrize(
    ("days", "should_flag"),
    [(29, False), (30, False), (31, True), (120, True)],
)
def test_handover_overdue_fires_at_the_30_day_boundary(db, days, should_flag):
    """The boundary is exclusive: 30 days is inside the window, 31 is not."""
    work = make_work(
        db, "W-1", status=WorkStatus.COMPLETED, sanctioned=date(2024, 6, 1),
        completed=TODAY - timedelta(days=days),
    )
    found = "HANDOVER_OVERDUE" in codes(handover.evaluate(work, ctx_for(db)))
    assert found is should_flag


def test_handover_acknowledged_but_not_registered(db):
    work = make_work(
        db, "W-1", status=WorkStatus.COMPLETED, sanctioned=date(2024, 6, 1),
        completed=TODAY - timedelta(days=90),
    )
    add_handover(
        db, work, initiated=TODAY - timedelta(days=85),
        acknowledged=TODAY - timedelta(days=80), uc=TODAY - timedelta(days=70),
        register=None,
    )
    assert "REGISTER_GAP" in codes(handover.evaluate(work, ctx_for(db)))


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def test_compliance_finding_forces_at_least_high(db):
    """A broken rule is a determinate fact and must not hide under a low score."""
    from app.engine.base import Finding, ModuleResult
    from app.engine.engine_config import load_config

    config = load_config(db)
    results = [
        ModuleResult(ModuleCode.COST, 0.0),
        ModuleResult(ModuleCode.DUPLICATE, 0.0),
        ModuleResult(ModuleCode.AGENCY, 0.0),
        ModuleResult(
            ModuleCode.COMPLIANCE,
            5.0,
            [
                Finding(
                    code="WORK_TYPE_NOT_PERMISSIBLE",
                    module=ModuleCode.COMPLIANCE,
                    signal_value=1.0,
                    threshold_value=0.0,
                    severity=SeverityTier.HIGH,
                    params={"work_type": "MEMORIAL_STATUE"},
                )
            ],
        ),
        ModuleResult(ModuleCode.STATISTICAL, 0.0),
    ]
    assessment = score("W-1", Stage.STAGE_1, results, config)

    assert assessment.composite_score < 26  # the score alone says LOW
    assert assessment.severity_tier is SeverityTier.HIGH
    assert assessment.override_applied


def test_agency_contribution_is_capped_regardless_of_weight(db):
    """Retuning the weight upward must not let the agency signal dominate."""
    from app.engine.base import ModuleResult
    from app.engine.engine_config import load_config

    config = load_config(db)
    config.stage1["AGENCY"] = 0.90  # as if someone set it absurdly high

    results = [ModuleResult(ModuleCode.AGENCY, 100.0)]
    assessment = score("W-1", Stage.STAGE_1, results, config)

    # 100 * 0.15 cap = 15, not 100 * 0.90 = 90.
    assert assessment.composite_score == pytest.approx(15.0)
    _, _, applied_weight = assessment.contributions[0]
    assert applied_weight == pytest.approx(0.15)
