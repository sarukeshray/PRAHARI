"""VARIANCE — did the work cost what it was sanctioned to cost?

The one place a rupee-to-rupee comparison is correct, because both figures belong
to the same work and the same sanction. No inflation adjustment applies: an
estimate and its own final cost are already in the same terms.

A revised estimate is a legitimate route for a genuine change in scope. The
finding is specifically an overrun with *no revision on record* — the paperwork
gap, not the extra spending.
"""

from __future__ import annotations

from app.engine.base import Finding, ModuleResult, score_from_exceedance, tier_from_exceedance
from app.engine.context import EngineContext
from app.engine.explain import rupees
from app.models.enums import ModuleCode
from app.models.works import Work

MODULE = ModuleCode.VARIANCE


def evaluate(work: Work, ctx: EngineContext) -> ModuleResult:
    if work.final_cost is None or work.estimated_cost <= 0:
        return ModuleResult(MODULE, 0.0, [])

    variance_pct = (work.final_cost - work.estimated_cost) / work.estimated_cost * 100
    limit = ctx.config.t("COST_OVERRUN_PCT")

    if variance_pct <= limit:
        return ModuleResult(MODULE, 0.0, [])

    finding = Finding(
        code="COST_OVERRUN",
        module=MODULE,
        signal_value=round(variance_pct, 2),
        threshold_value=limit,
        severity=tier_from_exceedance(variance_pct, limit),
        params={
            "final_cost": rupees(work.final_cost),
            "estimated_cost": rupees(work.estimated_cost),
            "variance_pct": variance_pct,
            "threshold": limit,
        },
    )
    return ModuleResult(
        MODULE, score_from_exceedance(variance_pct, limit, ceiling=4.0), [finding]
    )
