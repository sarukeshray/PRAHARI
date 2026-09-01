"""Composite scoring and severity tiering.

Three rules beyond the weighted sum, each with a reason:

**The agency cap.** The AGENCY module's contribution is clamped at 15% of the
composite regardless of its configured weight. The Ministry can retune weights
through the interface, and this cap makes it impossible to retune an agency's
historical record into a decisive factor. The fairness argument in
``agency_performance.py`` depends on the cap actually being enforced somewhere,
and this is that somewhere.

**The compliance override.** Any COMPLIANCE finding lifts the work to at least
HIGH. A broken rule is a determinate fact, not a statistical inference, and it
should not be able to hide beneath a low weighted score.

**Stage 2 compliance carries no weight.** Two compliance checks apply after
sanction, but the specified Stage 2 weights have no COMPLIANCE slot and are left
exactly as written. The findings still act, through the override above.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.engine.base import Finding, ModuleResult
from app.engine.engine_config import Config
from app.models.enums import ModuleCode, SeverityTier, Stage

TIER_ORDER = [SeverityTier.LOW, SeverityTier.MEDIUM, SeverityTier.HIGH, SeverityTier.CRITICAL]


@dataclass
class Assessment:
    """The engine's complete verdict on one work at one stage."""

    work_id: str
    stage: Stage
    composite_score: float
    severity_tier: SeverityTier
    engine_version: str
    contributions: list[tuple[ModuleCode, float, float]] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    #: Set when the compliance override raised the tier above what the score gave.
    tier_from_score: SeverityTier | None = None

    @property
    def override_applied(self) -> bool:
        return self.tier_from_score is not None and self.tier_from_score != self.severity_tier


def score(
    work_id: str,
    stage: Stage,
    results: list[ModuleResult],
    config: Config,
) -> Assessment:
    weights = config.weights_for(stage.value)
    agency_cap = config.caps.get("AGENCY_MAX_CONTRIBUTION", 0.15)

    contributions: list[tuple[ModuleCode, float, float]] = []
    total = 0.0

    for result in results:
        weight = weights.get(result.module, 0.0)

        # Enforced here rather than trusted to the configuration, so a weight
        # change through the Ministry screen cannot lift it.
        if result.module is ModuleCode.AGENCY:
            weight = min(weight, agency_cap)

        contributions.append((result.module, result.score, weight))
        total += result.score * weight

    composite = round(max(0.0, min(100.0, total)), 2)
    tier_from_score = config.tier_for(composite)
    tier = tier_from_score

    findings = [f for r in results for f in r.findings]

    if any(f.module is ModuleCode.COMPLIANCE for f in findings):
        if TIER_ORDER.index(tier) < TIER_ORDER.index(SeverityTier.HIGH):
            tier = SeverityTier.HIGH

    # A CRITICAL finding is never presented inside a MEDIUM work. The tier is a
    # reviewer's queue position, and burying an urgent finding under a calm
    # headline is how it gets missed.
    for finding in findings:
        if TIER_ORDER.index(finding.severity) > TIER_ORDER.index(tier):
            tier = finding.severity

    return Assessment(
        work_id=work_id,
        stage=stage,
        composite_score=composite,
        severity_tier=tier,
        engine_version=config.engine_version,
        contributions=contributions,
        findings=findings,
        tier_from_score=tier_from_score,
    )
