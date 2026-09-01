"""HANDOVER — was the finished asset actually given to anyone?

The gap this stage exists for. A work can be built correctly, paid correctly and
closed correctly, and still end up with nobody responsible for it, because the
handover to the operating body was never recorded. CAG has found this repeatedly:
the asset exists, the file is complete, and no register entry says who owns it.

Nothing here concerns maintenance funding. MPLADS cannot fund maintenance, and
the engine does not pretend otherwise. These findings are about the paperwork
that establishes an owner — which is the precondition for anyone else's budget to
ever be spent on the asset.

Findings route into the District Authority's existing review queue and use the
same three actions as every other stage. There is no parallel workflow.
"""

from __future__ import annotations

from app.engine.base import Finding, ModuleResult, score_from_exceedance, tier_from_exceedance
from app.engine.context import EngineContext
from app.models.enums import HandoverStatus, ModuleCode, SeverityTier, WorkStatus
from app.models.works import Work

MODULE = ModuleCode.HANDOVER


def evaluate(work: Work, ctx: EngineContext) -> ModuleResult:
    # Only a finished work can be handed over.
    if work.status != WorkStatus.COMPLETED or work.actual_completion_date is None:
        return ModuleResult(MODULE, 0.0, [])

    days_since_completion = (ctx.reference_date - work.actual_completion_date).days
    overdue_days = ctx.config.t("HANDOVER_OVERDUE_DAYS")
    uc_days = ctx.config.t("UC_SUBMISSION_DAYS")

    handover = ctx.handovers.get(work.work_id)
    findings: list[Finding] = []
    scores: list[float] = []

    # --- 1. No handover, or one still unacknowledged past the window ---
    if days_since_completion > overdue_days:
        if handover is None:
            state = "recorded"
        elif handover.handover_acknowledged_date is None:
            state = "acknowledged by the receiving agency"
        else:
            state = None

        if state is not None:
            findings.append(
                Finding(
                    code="HANDOVER_OVERDUE",
                    module=MODULE,
                    signal_value=float(days_since_completion),
                    threshold_value=overdue_days,
                    severity=tier_from_exceedance(days_since_completion, overdue_days),
                    params={
                        "days_since_completion": days_since_completion,
                        "handover_state": state,
                        "threshold_days": overdue_days,
                    },
                )
            )
            scores.append(score_from_exceedance(days_since_completion, overdue_days, ceiling=6.0))

    # --- 2. Utilisation Certificate not on file ---
    if days_since_completion > uc_days and (
        handover is None or handover.uc_submitted_date is None
    ):
        findings.append(
            Finding(
                code="UC_MISSING",
                module=MODULE,
                signal_value=float(days_since_completion),
                threshold_value=uc_days,
                severity=SeverityTier.HIGH,
                params={
                    "days_since_completion": days_since_completion,
                    "threshold_days": uc_days,
                },
            )
        )
        scores.append(70.0)

    # --- 3. Handed over, but never entered in the asset register ---
    if (
        handover is not None
        and handover.handover_acknowledged_date is not None
        and handover.register_entry_date is None
    ):
        findings.append(
            Finding(
                code="REGISTER_GAP",
                module=MODULE,
                signal_value=1.0,
                threshold_value=0.0,
                severity=SeverityTier.MEDIUM,
                params={
                    "handover_date": handover.handover_acknowledged_date.strftime("%d %b %Y")
                },
            )
        )
        scores.append(45.0)

    return ModuleResult(MODULE, max(scores) if scores else 0.0, findings)


def status_for(work: Work, ctx: EngineContext) -> HandoverStatus | None:
    """The handover state, for the District Authority's handover queue."""
    if work.status != WorkStatus.COMPLETED or work.actual_completion_date is None:
        return None
    handover = ctx.handovers.get(work.work_id)
    overdue_days = ctx.config.t("HANDOVER_OVERDUE_DAYS")
    days = (ctx.reference_date - work.actual_completion_date).days

    if handover is None:
        return HandoverStatus.OVERDUE if days > overdue_days else HandoverStatus.PENDING
    if handover.handover_acknowledged_date is not None:
        return HandoverStatus.ACKNOWLEDGED
    return HandoverStatus.OVERDUE if days > overdue_days else HandoverStatus.PENDING
