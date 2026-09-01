"""Orchestration: pick the stage for a work, run its modules, persist the result.

Which stage applies follows from the work's own status, because running
post-sanction checks on a proposal would be incoherent — a work that has not
started cannot have a payment-to-progress gap. A completed work is assessed at
Stage 3 as well, since handover is a separate question from execution.
"""

from __future__ import annotations

import logging

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.engine import explain
from app.engine.base import ModuleResult
from app.engine.context import EngineContext, build_context
from app.engine.scoring import Assessment, score
from app.engine.similarity import preload
from app.engine.stage1 import (
    agency_performance,
    compliance_rules,
    cost_benchmark,
    duplicate_detection,
    isolation_forest,
)
from app.engine.stage2 import cost_variance, geotag_verification, payment_progress, timeline
from app.engine.stage3 import handover
from app.models.enums import ModuleCode, Stage, WorkStatus
from app.models.risk import ModuleContribution, RiskAssessment, RiskFlag
from app.models.works import Work

logger = logging.getLogger(__name__)


def stages_for(work: Work) -> list[Stage]:
    """Which assessments apply to a work in its current state."""
    if work.status == WorkStatus.RECOMMENDED:
        return [Stage.STAGE_1]
    if work.status == WorkStatus.REJECTED:
        return []
    if work.status == WorkStatus.COMPLETED:
        return [Stage.STAGE_2, Stage.STAGE_3]
    return [Stage.STAGE_2]


def run_stage(
    work: Work,
    ctx: EngineContext,
    stage: Stage,
    model: isolation_forest.StatisticalModel | None = None,
) -> Assessment:
    if stage is Stage.STAGE_1:
        results = [
            cost_benchmark.evaluate(work, ctx),
            duplicate_detection.evaluate(work, ctx),
            agency_performance.evaluate(work, ctx),
            compliance_rules.evaluate(work, ctx),
            isolation_forest.evaluate(work, ctx, model),
        ]
    elif stage is Stage.STAGE_2:
        results = [
            payment_progress.evaluate(work, ctx),
            geotag_verification.evaluate(work, ctx),
            cost_variance.evaluate(work, ctx),
            timeline.evaluate(work, ctx),
            # Carries zero weight at this stage; acts through the tier override.
            compliance_rules.evaluate(work, ctx),
        ]
    else:
        results = [handover.evaluate(work, ctx)]

    return score(work.work_id, stage, results, ctx.config)


def persist(db: Session, assessment: Assessment) -> RiskAssessment:
    """Write an assessment, replacing any earlier one for the same work and stage.

    Reviews already recorded against a previous finding are preserved by leaving
    decided findings in place: only OPEN findings are replaced on a re-run, so a
    reviewer's decision is never silently discarded by rescoring.
    """
    previous = db.scalars(
        select(RiskAssessment).where(
            RiskAssessment.work_id == assessment.work_id,
            RiskAssessment.stage == assessment.stage,
        )
    ).all()
    for old in previous:
        db.execute(delete(ModuleContribution).where(
            ModuleContribution.assessment_id == old.assessment_id
        ))
        db.execute(delete(RiskFlag).where(
            RiskFlag.assessment_id == old.assessment_id,
            RiskFlag.status == "OPEN",
        ))
        db.delete(old)
    db.flush()

    row = RiskAssessment(
        work_id=assessment.work_id,
        stage=assessment.stage,
        composite_score=assessment.composite_score,
        severity_tier=assessment.severity_tier,
        engine_version=assessment.engine_version,
    )
    db.add(row)
    db.flush()

    for module, module_score, weight in assessment.contributions:
        db.add(
            ModuleContribution(
                assessment_id=row.assessment_id,
                module=module,
                score=round(module_score, 2),
                weight=weight,
            )
        )

    for finding in assessment.findings:
        db.add(
            RiskFlag(
                assessment_id=row.assessment_id,
                work_id=assessment.work_id,
                module=finding.module,
                flag_code=finding.code,
                signal_value=finding.signal_value,
                threshold_value=finding.threshold_value,
                severity_tier=finding.severity,
                explanation=explain.render(finding.code, finding.params),
            )
        )

    return row


def assess_work(db: Session, work: Work, ctx: EngineContext, model=None) -> list[Assessment]:
    out = []
    for stage in stages_for(work):
        assessment = run_stage(work, ctx, stage, model)
        persist(db, assessment)
        out.append(assessment)
    return out


def assess_all(db: Session, limit: int | None = None, progress_every: int = 500) -> dict:
    """Score the whole corpus. Returns a summary for the caller to print."""
    ctx = build_context(db)
    works = db.scalars(select(Work)).all()
    if limit:
        works = works[:limit]

    logger.info("preloading description embeddings for %d works", len(works))
    preload([w.description for w in works])

    # Fit on the population Stage 1 actually screens - works still awaiting
    # sanction. Training on the whole corpus made every proposal look unusual
    # simply for being recent, because recency correlates with being unscreened.
    trainable = [w for w in works if w.status == WorkStatus.RECOMMENDED]
    model = isolation_forest.StatisticalModel()
    if len(trainable) >= 50:
        model.fit(trainable, ctx)

    summary = {"works": 0, "assessments": 0, "findings": 0, "by_tier": {}, "by_code": {}}

    for n, work in enumerate(works, start=1):
        for assessment in assess_work(db, work, ctx, model):
            summary["assessments"] += 1
            summary["findings"] += len(assessment.findings)
            tier = assessment.severity_tier.value
            summary["by_tier"][tier] = summary["by_tier"].get(tier, 0) + 1
            for finding in assessment.findings:
                summary["by_code"][finding.code] = summary["by_code"].get(finding.code, 0) + 1
        summary["works"] += 1
        if n % progress_every == 0:
            db.flush()
            logger.info("  scored %d/%d works", n, len(works))

    db.commit()
    return summary
