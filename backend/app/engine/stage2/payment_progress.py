"""DISBURSEMENT — is the money moving faster than the work?

The clearest post-sanction signal there is. Funds released should track physical
progress; a widening gap between them is the shape most documented MPLADS
irregularities take, and unlike a cost estimate it needs no benchmark to
interpret. Both figures come from the implementing agency's own returns.
"""

from __future__ import annotations

from app.engine.base import Finding, ModuleResult, score_from_exceedance, tier_from_exceedance
from app.engine.context import EngineContext
from app.engine.explain import rupees
from app.models.enums import ModuleCode, SeverityTier, WorkStatus
from app.models.works import Work

MODULE = ModuleCode.DISBURSEMENT


def evaluate(work: Work, ctx: EngineContext) -> ModuleResult:
    if work.sanctioned_date is None or work.estimated_cost <= 0:
        return ModuleResult(MODULE, 0.0, [])

    agg = ctx.aggregates.get(work.work_id)
    if agg is None:
        return ModuleResult(MODULE, 0.0, [])

    disbursed_pct = min(100.0, agg.disbursed / work.estimated_cost * 100)
    progress_pct = agg.latest_progress
    divergence = disbursed_pct - progress_pct

    findings: list[Finding] = []
    scores: list[float] = []

    gap_limit = ctx.config.t("PAYMENT_AHEAD_POINTS")
    if divergence > gap_limit:
        findings.append(
            Finding(
                code="PAYMENT_AHEAD_OF_PROGRESS",
                module=MODULE,
                signal_value=round(divergence, 2),
                threshold_value=gap_limit,
                severity=tier_from_exceedance(divergence, gap_limit),
                params={
                    "disbursed_pct": disbursed_pct,
                    "progress_pct": progress_pct,
                    "divergence": divergence,
                    "threshold": gap_limit,
                },
            )
        )
        scores.append(score_from_exceedance(divergence, gap_limit, ceiling=3.0))

    # Fully paid but unfinished is its own finding, not a louder version of the
    # one above: there is no remaining leverage to get the work completed.
    incomplete_at = ctx.config.t("FULLY_PAID_PROGRESS_PCT")
    if disbursed_pct >= 99.5 and progress_pct < incomplete_at:
        findings.append(
            Finding(
                code="FULLY_PAID_INCOMPLETE",
                module=MODULE,
                signal_value=round(progress_pct, 2),
                threshold_value=incomplete_at,
                severity=SeverityTier.CRITICAL
                if work.status != WorkStatus.COMPLETED
                else SeverityTier.HIGH,
                params={
                    "estimated_cost": rupees(work.estimated_cost),
                    "progress_pct": progress_pct,
                },
            )
        )
        scores.append(90.0)

    return ModuleResult(MODULE, max(scores) if scores else 0.0, findings)
