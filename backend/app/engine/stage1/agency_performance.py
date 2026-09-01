"""AGENCY — how has this implementing agency performed, against comparable agencies?

The most dangerous module in the system, and the one most tightly constrained.

An agency working in remote or hilly terrain will show more delay and more cost
variance than one working on the plains, for reasons that have nothing to do with
its conduct. Rank it nationally and that terrain becomes a permanent penalty;
because the score feeds future scrutiny, and scrutiny produces findings, the
penalty compounds into a feedback loop that the agency cannot escape by
performing well.

Three constraints stop that:

1. **Peer group, never national.** An agency is ranked only against agencies
   working in the same terrain category.
2. **Never on thin history.** No finding below fifteen completed works, because
   a percentile over four works measures noise.
3. **Never decisive.** The contribution is capped at 15% of the composite in
   ``scoring.py``, independently of the configured weight, so retuning through
   the Ministry screen cannot turn a record into a verdict.

The label is ``agency_historical_performance``. It is not a trust score, and the
interface never calls it one.
"""

from __future__ import annotations

from app.engine.base import Finding, ModuleResult
from app.engine.context import EngineContext
from app.models.enums import ModuleCode, SeverityTier
from app.models.works import Work

MODULE = ModuleCode.AGENCY


def evaluate(work: Work, ctx: EngineContext) -> ModuleResult:
    if not work.agency_id:
        return ModuleResult(MODULE, 0.0, [])

    stats = ctx.agency_stats.get(work.agency_id)
    if stats is None:
        return ModuleResult(MODULE, 0.0, [])

    floor = ctx.config.t("AGENCY_PERCENTILE_FLOOR")
    min_completed = ctx.config.t("AGENCY_MIN_COMPLETED_WORKS")

    # A weak percentile still contributes to the score below; it only becomes a
    # visible finding when there is enough history to stand behind it.
    score = max(0.0, min(100.0, 100.0 - stats.percentile))

    if stats.percentile >= floor or stats.completed < min_completed:
        return ModuleResult(MODULE, score, [])

    district = ctx.districts[work.district_id]
    cap_pct = ctx.config.caps.get("AGENCY_MAX_CONTRIBUTION", 0.15) * 100

    finding = Finding(
        code="AGENCY_HISTORICAL_CONCERN",
        module=MODULE,
        signal_value=round(stats.percentile, 2),
        threshold_value=floor,
        # Capped at MEDIUM by design. A record is context for a reviewer, never
        # the reason a work becomes urgent on its own.
        severity=SeverityTier.MEDIUM,
        params={
            "percentile": stats.percentile,
            "peer_count": stats.peer_count,
            "terrain": district.terrain_category.value,
            "completed_count": stats.completed,
            "cap_pct": cap_pct,
        },
    )
    return ModuleResult(MODULE, score, [finding])
