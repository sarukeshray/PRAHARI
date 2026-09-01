"""TIMELINE — is the work progressing, and is anyone still reporting on it?

Three findings, ordered by how much they should worry a reviewer.

``COMPLETION_OVERDUE_12M`` is slippage — common, often legitimate, worth
tracking. ``PROGRESS_REPORTING_STALLED`` is the reporting line going quiet, which
is what tends to precede a work quietly stopping. ``GHOST_WORK`` is the endpoint:
a work marked complete and fully paid, with no evidence that anything was ever
built.

``GHOST_WORK`` is defined here rather than in a module of its own because it is a
conjunction of conditions this module already holds. The original specification
named the pattern in the backtest cases but never defined a flag code for it.
"""

from __future__ import annotations

from app.engine.base import Finding, ModuleResult, score_from_exceedance, tier_from_exceedance
from app.engine.context import EngineContext
from app.models.enums import ModuleCode, SeverityTier, WorkStatus
from app.models.works import Work

MODULE = ModuleCode.TIMELINE


def evaluate(work: Work, ctx: EngineContext) -> ModuleResult:
    if work.sanctioned_date is None:
        return ModuleResult(MODULE, 0.0, [])

    agg = ctx.aggregates.get(work.work_id)
    if agg is None:
        return ModuleResult(MODULE, 0.0, [])

    findings: list[Finding] = []
    scores: list[float] = []

    disbursed_pct = (
        min(100.0, agg.disbursed / work.estimated_cost * 100) if work.estimated_cost else 0.0
    )

    # --- Ghost work: complete and paid, with nothing to show for it ---
    if (
        work.status == WorkStatus.COMPLETED
        and disbursed_pct >= 99.5
        and agg.report_count == 0
        and agg.photo_count == 0
    ):
        findings.append(
            Finding(
                code="GHOST_WORK",
                module=MODULE,
                signal_value=0.0,
                threshold_value=1.0,
                severity=SeverityTier.CRITICAL,
                params={"disbursed_pct": disbursed_pct},
            )
        )
        scores.append(100.0)

    # --- Marked complete with no photograph ---
    elif work.status == WorkStatus.COMPLETED and agg.photo_count == 0:
        findings.append(
            Finding(
                code="NO_COMPLETION_EVIDENCE",
                module=MODULE,
                signal_value=0.0,
                threshold_value=1.0,
                severity=SeverityTier.HIGH,
                params={"report_count": agg.report_count},
            )
        )
        scores.append(80.0)

    # --- Overdue against the twelve-month guideline ---
    if work.status != WorkStatus.COMPLETED:
        days_since = (ctx.reference_date - work.sanctioned_date).days
        limit = ctx.config.t("COMPLETION_GUIDELINE_DAYS")
        if days_since > limit:
            findings.append(
                Finding(
                    code="COMPLETION_OVERDUE_12M",
                    module=MODULE,
                    signal_value=float(days_since),
                    threshold_value=limit,
                    severity=tier_from_exceedance(days_since, limit),
                    params={
                        "days_since_sanction": days_since,
                        "progress_pct": agg.latest_progress,
                        "threshold_days": limit,
                    },
                )
            )
            scores.append(score_from_exceedance(days_since, limit, ceiling=2.5))

        # --- Reporting gone quiet ---
        last = agg.last_report_date or work.sanctioned_date
        silence = (ctx.reference_date - last).days
        stale_limit = ctx.config.t("PROGRESS_STALE_DAYS")
        if silence > stale_limit:
            findings.append(
                Finding(
                    code="PROGRESS_REPORTING_STALLED",
                    module=MODULE,
                    signal_value=float(silence),
                    threshold_value=stale_limit,
                    severity=tier_from_exceedance(silence, stale_limit),
                    params={
                        "days_since_report": silence,
                        "progress_pct": agg.latest_progress,
                        "threshold": stale_limit,
                    },
                )
            )
            scores.append(score_from_exceedance(silence, stale_limit, ceiling=3.0))

    return ModuleResult(MODULE, max(scores) if scores else 0.0, findings)
