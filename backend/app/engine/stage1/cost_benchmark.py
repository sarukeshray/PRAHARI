"""COST — is this estimate plausible for this work, here, now?

Two independent checks. The first compares the estimate against the published
Schedule of Rates; the second asks whether it is unusual against comparable works
even if the benchmark says otherwise.

Both operate on the **ratio** of cost to the benchmark for the work's own year,
never on rupee amounts across years. That is the whole inflation defence: when
rates rise 6% and every estimate rises 6% with them, the ratio does not move, so
no flag fires. A deflator would approximate this; using the same-year benchmark
makes it exact.
"""

from __future__ import annotations

from app.engine.base import Finding, ModuleResult, score_from_exceedance, tier_from_exceedance
from app.engine.context import EngineContext
from app.engine.explain import rupees
from app.models.enums import ModuleCode, SeverityTier
from app.models.works import Work

MODULE = ModuleCode.COST


def evaluate(work: Work, ctx: EngineContext) -> ModuleResult:
    findings: list[Finding] = []
    scores: list[float] = []

    bench = ctx.benchmark(work)
    if bench is None or bench[0] <= 0:
        # No published rate for this combination. Silence is correct here — a
        # missing benchmark is not evidence of anything about the work.
        return ModuleResult(MODULE, 0.0, [])

    benchmark, sor_year = bench
    district = ctx.districts[work.district_id]
    ratio = work.estimated_cost / benchmark
    deviation_pct = (ratio - 1.0) * 100

    above = ctx.config.t("COST_ABOVE_SOR_PCT")
    below = ctx.config.t("COST_BELOW_SOR_PCT")

    params = {
        "estimated_cost": rupees(work.estimated_cost),
        "benchmark": rupees(benchmark),
        "state": district.state,
        "work_type": work.work_type,
        "terrain": district.terrain_category.value,
        "sor_year": sor_year,
    }

    if deviation_pct > above:
        findings.append(
            Finding(
                code="COST_ABOVE_SOR",
                module=MODULE,
                signal_value=round(deviation_pct, 2),
                threshold_value=above,
                severity=tier_from_exceedance(deviation_pct, above),
                params={**params, "deviation_pct": deviation_pct},
            )
        )
        scores.append(score_from_exceedance(deviation_pct, above, ceiling=4.0))

    elif deviation_pct < below:
        # An estimate far under benchmark is a scoping concern, not a saving:
        # the work is likely to stall or need a revision once it starts.
        findings.append(
            Finding(
                code="COST_BELOW_SOR",
                module=MODULE,
                signal_value=round(deviation_pct, 2),
                threshold_value=below,
                severity=SeverityTier.MEDIUM,
                params={**params, "deviation_abs": abs(deviation_pct)},
            )
        )
        scores.append(score_from_exceedance(deviation_pct, below, ceiling=2.5))

    # --- peer-group outlier, on the same ratio ---
    peer = ctx.peer_cost.get((work.work_type, district.terrain_category))
    if peer:
        median, mad, peer_count = peer
        if mad > 0:
            # Modified z-score. 0.6745 is the constant that makes MAD a
            # consistent estimator of the standard deviation for normal data.
            modified_z = 0.6745 * (ratio - median) / mad
            limit = ctx.config.t("COST_PEER_MODIFIED_Z")
            if modified_z > limit:
                findings.append(
                    Finding(
                        code="COST_PEER_OUTLIER",
                        module=MODULE,
                        signal_value=round(modified_z, 2),
                        threshold_value=limit,
                        severity=tier_from_exceedance(modified_z, limit),
                        params={
                            "modified_z": modified_z,
                            "work_type": work.work_type,
                            "terrain": district.terrain_category.value,
                            "peer_count": peer_count,
                            "threshold": limit,
                        },
                    )
                )
                scores.append(score_from_exceedance(modified_z, limit, ceiling=3.0))

    return ModuleResult(MODULE, max(scores) if scores else 0.0, findings)
