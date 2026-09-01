"""Works, findings, and the review workflow.

Every read is narrowed by ``Scope`` before it touches the database. Every write
that changes a finding's state records who did it and why.

Nothing here ever changes a finding's state on its own. The three review actions
are the only transitions, and all three require a person.
"""

from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import CurrentUser, Scope, current_user, require_roles, scope
from app.db import get_db
from app.engine import runner
from app.engine.context import REFERENCE_DATE, build_context
from app.models import MP, Agency, District, Payment, ProgressReport, Work
from app.models.enums import FlagStatus, ModuleCode, ReviewAction, Role, SeverityTier, WorkStatus
from app.models.risk import FlagReview, RiskAssessment, RiskFlag
from app.schemas.api import (
    AssessmentOut,
    FlagOut,
    ReassignRequest,
    ReviewRequest,
    WorkDetail,
    WorkRecommendation,
    WorkSummary,
)

router = APIRouter()

TIER_RANK = {
    SeverityTier.CRITICAL: 0,
    SeverityTier.HIGH: 1,
    SeverityTier.MEDIUM: 2,
    SeverityTier.LOW: 3,
}


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------


def _latest_assessments(db: Session, work_ids: list[str]) -> dict[str, RiskAssessment]:
    """The most severe current assessment per work.

    A work can carry both a Stage 2 and a Stage 3 assessment. The queue shows the
    one that most needs attention, not the most recent, because recency is not
    what a reviewer is sorting by.
    """
    if not work_ids:
        return {}
    rows = db.scalars(
        select(RiskAssessment)
        .where(RiskAssessment.work_id.in_(work_ids))
        .options(selectinload(RiskAssessment.flags), selectinload(RiskAssessment.contributions))
    ).all()
    # Newest per (work, stage) first - a superseded assessment lingers only
    # because it carries a reviewed finding, and must not drive the headline.
    newest: dict[tuple[str, object], RiskAssessment] = {}
    for row in rows:
        key = (row.work_id, row.stage)
        held = newest.get(key)
        if held is None or row.computed_at > held.computed_at:
            newest[key] = row

    best: dict[str, RiskAssessment] = {}
    for row in newest.values():
        held = best.get(row.work_id)
        if held is None or TIER_RANK[row.severity_tier] < TIER_RANK[held.severity_tier]:
            best[row.work_id] = row
    return best


def _summary(work: Work, assessment: RiskAssessment | None, names: dict) -> WorkSummary:
    open_flags = [f for f in (assessment.flags if assessment else []) if f.status == FlagStatus.OPEN]
    open_flags.sort(key=lambda f: TIER_RANK[f.severity_tier])
    primary = open_flags[0] if open_flags else None

    basis = work.recommended_date or work.sanctioned_date
    return WorkSummary(
        work_id=work.work_id,
        work_type=work.work_type,
        description=work.description,
        block=work.block,
        district_id=work.district_id,
        district_name=names["districts"].get(work.district_id),
        estimated_cost=work.estimated_cost,
        final_cost=work.final_cost,
        status=work.status,
        recommended_date=work.recommended_date,
        sanctioned_date=work.sanctioned_date,
        mp_name=names["mps"].get(work.mp_id) if work.mp_id else None,
        agency_name=names["agencies"].get(work.agency_id) if work.agency_id else None,
        latitude=work.latitude,
        longitude=work.longitude,
        is_sc_st_area=work.is_sc_st_area,
        severity_tier=assessment.severity_tier if assessment else None,
        composite_score=assessment.composite_score if assessment else None,
        open_flag_count=len(open_flags),
        primary_finding=primary.explanation if primary else None,
        primary_finding_title=primary.flag_code if primary else None,
        days_open=(REFERENCE_DATE - basis).days if basis else None,
    )


def _name_maps(db: Session) -> dict:
    return {
        "districts": dict(db.execute(select(District.district_id, District.name)).all()),
        "mps": dict(db.execute(select(MP.mp_id, MP.name)).all()),
        "agencies": dict(db.execute(select(Agency.agency_id, Agency.name)).all()),
    }


# ---------------------------------------------------------------------------
# Works
# ---------------------------------------------------------------------------


@router.get("/works", response_model=list[WorkSummary], tags=["works"])
def list_works(
    db: Session = Depends(get_db),
    sc: Scope = Depends(scope),
    district: str | None = None,
    status_filter: WorkStatus | None = Query(default=None, alias="status"),
    severity: SeverityTier | None = None,
    module: ModuleCode | None = None,
    work_type: str | None = None,
    block: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    only_findings: bool = False,
    search: str | None = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
) -> list[WorkSummary]:
    stmt = sc.works(select(Work))

    if district:
        stmt = stmt.where(Work.district_id == district)
    if status_filter:
        stmt = stmt.where(Work.status == status_filter)
    if work_type:
        stmt = stmt.where(Work.work_type == work_type)
    if block:
        stmt = stmt.where(Work.block == block)
    if from_date:
        stmt = stmt.where(Work.recommended_date >= from_date)
    if to_date:
        stmt = stmt.where(Work.recommended_date <= to_date)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(Work.description.ilike(like) | Work.work_id.ilike(like))

    if severity or module or only_findings:
        flagged = select(RiskFlag.work_id).where(RiskFlag.status == FlagStatus.OPEN)
        if module:
            flagged = flagged.where(RiskFlag.module == module)
        if severity:
            flagged = flagged.where(RiskFlag.severity_tier == severity)
        stmt = stmt.where(Work.work_id.in_(flagged))

    works = db.scalars(stmt.limit(limit).offset(offset)).all()
    assessments = _latest_assessments(db, [w.work_id for w in works])
    names = _name_maps(db)

    rows = [_summary(w, assessments.get(w.work_id), names) for w in works]
    rows.sort(
        key=lambda r: (
            TIER_RANK.get(r.severity_tier, 99),
            -(r.days_open or 0),
        )
    )
    return rows


@router.get("/works/{work_id}", response_model=WorkDetail, tags=["works"])
def get_work(
    work_id: str,
    db: Session = Depends(get_db),
    sc: Scope = Depends(scope),
) -> WorkDetail:
    work = sc.require_work(db, work_id)
    names = _name_maps(db)

    assessments = db.scalars(
        select(RiskAssessment)
        .where(RiskAssessment.work_id == work_id)
        .options(
            selectinload(RiskAssessment.flags).selectinload(RiskFlag.reviews),
            selectinload(RiskAssessment.contributions),
        )
        .order_by(RiskAssessment.stage)
    ).all()

    best = None
    for a in assessments:
        if best is None or TIER_RANK[a.severity_tier] < TIER_RANK[best.severity_tier]:
            best = a

    disbursed = db.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0.0)).where(Payment.work_id == work_id)
    ) or 0.0
    progress = db.scalar(
        select(func.coalesce(func.max(ProgressReport.physical_progress_pct), 0.0)).where(
            ProgressReport.work_id == work_id
        )
    ) or 0.0
    report_count = db.scalar(
        select(func.count()).select_from(ProgressReport).where(ProgressReport.work_id == work_id)
    ) or 0

    from app.models import CompletionPhoto

    photo_count = db.scalar(
        select(func.count()).select_from(CompletionPhoto).where(CompletionPhoto.work_id == work_id)
    ) or 0

    district = db.get(District, work.district_id)
    mp = db.get(MP, work.mp_id) if work.mp_id else None
    agency = db.get(Agency, work.agency_id) if work.agency_id else None

    base = _summary(work, best, names)
    return WorkDetail(
        **base.model_dump(),
        panchayat=work.panchayat,
        state=district.state if district else None,
        terrain_category=district.terrain_category.value if district else None,
        constituency=mp.constituency if mp else None,
        house=mp.house.value if mp else None,
        agency_type=agency.agency_type.value if agency else None,
        expected_completion_date=work.expected_completion_date,
        actual_completion_date=work.actual_completion_date,
        disbursed_amount=disbursed,
        disbursed_pct=(disbursed / work.estimated_cost * 100) if work.estimated_cost else 0.0,
        latest_progress_pct=progress,
        photo_count=photo_count,
        report_count=report_count,
        assessments=[AssessmentOut.model_validate(a) for a in assessments],
    )


@router.post("/works/{work_id}/assess", response_model=list[AssessmentOut], tags=["works"])
def assess_work(
    work_id: str,
    db: Session = Depends(get_db),
    sc: Scope = Depends(scope),
) -> list[AssessmentOut]:
    """Re-run the appropriate stage engine and persist the result.

    Decided findings survive a re-run: only OPEN ones are replaced, so rescoring
    never quietly discards a reviewer's decision.
    """
    work = sc.require_work(db, work_id)
    ctx = build_context(db)
    runner.assess_work(db, work, ctx, model=None)
    db.commit()

    rows = db.scalars(
        select(RiskAssessment)
        .where(RiskAssessment.work_id == work_id)
        .options(
            selectinload(RiskAssessment.flags).selectinload(RiskFlag.reviews),
            selectinload(RiskAssessment.contributions),
        )
    ).all()
    return [AssessmentOut.model_validate(r) for r in rows]


@router.post(
    "/works",
    response_model=WorkDetail,
    status_code=status.HTTP_201_CREATED,
    tags=["works"],
)
def recommend_work(
    payload: WorkRecommendation,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Role.MP)),
    sc: Scope = Depends(scope),
) -> WorkDetail:
    """A Member submits a recommendation. Screening runs immediately.

    The work is created regardless of what screening finds. A finding routes to
    the District Authority; it never blocks a submission, because the system has
    no authority to refuse one.
    """
    district = db.get(District, payload.district_id)
    if district is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown district.")

    serial = (db.scalar(select(func.count()).select_from(Work)) or 0) + 1
    work = Work(
        work_id=f"{payload.district_id}-{serial:05d}",
        mp_id=user.scope_mp_id,
        district_id=payload.district_id,
        block=payload.block,
        panchayat=payload.panchayat or payload.block,
        work_type=payload.work_type,
        description=payload.description,
        estimated_cost=payload.estimated_cost,
        recommended_date=REFERENCE_DATE,
        status=WorkStatus.RECOMMENDED,
        agency_id=payload.agency_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        is_sc_st_area=payload.is_sc_st_area,
    )
    db.add(work)
    db.flush()

    ctx = build_context(db)
    runner.assess_work(db, work, ctx, model=None)
    db.commit()

    return get_work(work.work_id, db=db, sc=sc)


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------


@router.get("/flags", response_model=list[FlagOut], tags=["findings"])
def list_flags(
    db: Session = Depends(get_db),
    sc: Scope = Depends(scope),
    status_filter: FlagStatus | None = Query(default=None, alias="status"),
    severity: SeverityTier | None = None,
    module: ModuleCode | None = None,
    district: str | None = None,
    assigned_to: str | None = None,
    limit: int = Query(default=200, le=1000),
) -> list[FlagOut]:
    visible = sc.works(select(Work.work_id))
    stmt = (
        select(RiskFlag)
        .where(RiskFlag.work_id.in_(visible))
        .options(selectinload(RiskFlag.reviews))
    )
    if status_filter:
        stmt = stmt.where(RiskFlag.status == status_filter)
    if severity:
        stmt = stmt.where(RiskFlag.severity_tier == severity)
    if module:
        stmt = stmt.where(RiskFlag.module == module)
    if assigned_to:
        stmt = stmt.where(RiskFlag.assigned_to_user_id == assigned_to)
    if district:
        stmt = stmt.where(
            RiskFlag.work_id.in_(select(Work.work_id).where(Work.district_id == district))
        )

    flags = db.scalars(stmt.limit(limit)).all()
    flags.sort(key=lambda f: (TIER_RANK[f.severity_tier], f.created_at))
    return [FlagOut.model_validate(f) for f in flags]


@router.get("/flags/{flag_id}", response_model=FlagOut, tags=["findings"])
def get_flag(
    flag_id: int,
    db: Session = Depends(get_db),
    sc: Scope = Depends(scope),
) -> FlagOut:
    flag = db.get(RiskFlag, flag_id)
    if flag is None or not sc.may_see_work(db, flag.work_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such finding.")
    return FlagOut.model_validate(flag)


NEXT_STATUS = {
    ReviewAction.INVESTIGATE: FlagStatus.UNDER_INVESTIGATION,
    ReviewAction.OVERRIDE: FlagStatus.OVERRIDDEN,
    ReviewAction.CLEAR: FlagStatus.CLEARED,
}


@router.post("/flags/{flag_id}/review", response_model=FlagOut, tags=["findings"])
def review_flag(
    flag_id: int,
    payload: ReviewRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(
        require_roles(Role.DISTRICT_AUTHORITY, Role.STATE_NODAL, Role.MINISTRY)
    ),
    sc: Scope = Depends(scope),
) -> FlagOut:
    """Record a human decision on a finding.

    The only three transitions a finding can undergo, and each is written to the
    audit trail with who took it. An OVERRIDE without a written justification is
    refused with 422 here, not merely discouraged in the interface.
    """
    payload.validate_for_action()

    flag = db.get(RiskFlag, flag_id)
    if flag is None or not sc.may_see_work(db, flag.work_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such finding.")

    db.add(
        FlagReview(
            flag_id=flag.flag_id,
            reviewer_role=user.role,
            reviewer_name=payload.reviewer_name or user.display_name,
            action=payload.action,
            justification=payload.justification or None,
            decided_at=datetime.utcnow(),
        )
    )
    flag.status = NEXT_STATUS[payload.action]
    db.commit()
    db.refresh(flag)
    return FlagOut.model_validate(flag)


@router.post("/flags/{flag_id}/reassign", response_model=FlagOut, tags=["findings"])
def reassign_flag(
    flag_id: int,
    payload: ReassignRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Role.STATE_NODAL, Role.MINISTRY)),
    sc: Scope = Depends(scope),
) -> FlagOut:
    """Move a finding to a different reviewer. Does not change its state."""
    from app.models import User

    flag = db.get(RiskFlag, flag_id)
    if flag is None or not sc.may_see_work(db, flag.work_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such finding.")

    target = db.get(User, payload.assigned_to_user_id)
    if target is None or target.role is not Role.DISTRICT_AUTHORITY:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "A finding can only be reassigned to a District Authority reviewer.",
        )

    flag.assigned_to_user_id = target.user_id
    db.add(
        FlagReview(
            flag_id=flag.flag_id,
            reviewer_role=user.role,
            reviewer_name=user.display_name,
            action=ReviewAction.INVESTIGATE,
            justification=(
                payload.note or f"Reassigned to {target.display_name} for review."
            ),
            decided_at=datetime.utcnow(),
        )
    )
    db.commit()
    db.refresh(flag)
    return FlagOut.model_validate(flag)
