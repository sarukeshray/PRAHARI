"""Stage 3 — handover, check-ins, and maintenance needs.

The gap this covers: a work can be built, paid for and closed correctly and still
end up with nobody on record as its owner, because the handover was never
registered. Everything here is about establishing and then keeping that record.

**Maintenance is not funded from MPLADS.** A maintenance recommendation raised
here is a notification to the department whose budget can pay for it, and the
wording says so plainly wherever it appears.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, Scope, current_user, require_roles, scope
from app.db import get_db
from app.engine.context import REFERENCE_DATE
from app.models import (
    AssetHandover,
    LifecycleCheckin,
    MaintenanceRecommendation,
    UserAgency,
    Work,
)
from app.models.enums import HandoverStatus, Role, WorkStatus
from app.schemas.api import (
    AssetSummary,
    CheckinOut,
    CheckinRequest,
    HandoverOut,
    MaintenanceOut,
    MaintenanceRequest,
)

router = APIRouter()


def _handover_out(h: AssetHandover, name: str | None) -> HandoverOut:
    return HandoverOut(
        handover_id=h.handover_id,
        work_id=h.work_id,
        user_agency_id=h.user_agency_id,
        user_agency_name=name,
        handover_initiated_date=h.handover_initiated_date,
        handover_acknowledged_date=h.handover_acknowledged_date,
        uc_submitted_date=h.uc_submitted_date,
        register_entry_date=h.register_entry_date,
        status=h.status,
    )


@router.get("/assets", response_model=list[AssetSummary], tags=["lifecycle"])
def my_assets(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Role.USER_AGENCY)),
) -> list[AssetSummary]:
    """Assets handed over to the signed-in user agency, and nothing else."""
    handovers = db.scalars(
        select(AssetHandover).where(
            AssetHandover.user_agency_id == user.scope_user_agency_id
        )
    ).all()
    by_work = {h.work_id: h for h in handovers}
    if not by_work:
        return []

    works = db.scalars(select(Work).where(Work.work_id.in_(by_work))).all()
    checkins: dict[str, list[LifecycleCheckin]] = {}
    for c in db.scalars(select(LifecycleCheckin).where(LifecycleCheckin.work_id.in_(by_work))):
        checkins.setdefault(c.work_id, []).append(c)
    recs: dict[str, list[MaintenanceRecommendation]] = {}
    for r in db.scalars(
        select(MaintenanceRecommendation).where(MaintenanceRecommendation.work_id.in_(by_work))
    ):
        recs.setdefault(r.work_id, []).append(r)

    agency = db.get(UserAgency, user.scope_user_agency_id)
    name = agency.name if agency else None

    return [
        AssetSummary(
            work_id=w.work_id,
            work_type=w.work_type,
            description=w.description,
            block=w.block,
            completed_on=w.actual_completion_date,
            handover=_handover_out(by_work[w.work_id], name),
            checkins=[CheckinOut.model_validate(c) for c in sorted(
                checkins.get(w.work_id, []), key=lambda c: c.checkin_date
            )],
            maintenance=[MaintenanceOut.model_validate(r) for r in sorted(
                recs.get(w.work_id, []), key=lambda r: r.raised_date, reverse=True
            )],
        )
        for w in works
    ]


@router.post("/assets/{work_id}/acknowledge", response_model=HandoverOut, tags=["lifecycle"])
def acknowledge_handover(
    work_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Role.USER_AGENCY)),
) -> HandoverOut:
    """Confirm receipt of an asset.

    This single record is what closes the gap CAG documented: an asset with an
    acknowledged handover has somebody accountable for it, and one without does
    not, however complete the rest of the file looks.
    """
    handover = db.scalar(select(AssetHandover).where(AssetHandover.work_id == work_id))
    if handover is None:
        # No handover has been initiated, so the user agency has nothing to
        # acknowledge yet. Creating one from this side would let a receiving
        # body invent a transfer nobody offered.
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "No handover has been initiated for this work.",
        )
    if handover.user_agency_id != user.scope_user_agency_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such asset.")

    if handover.handover_acknowledged_date is None:
        handover.handover_acknowledged_date = REFERENCE_DATE
        handover.status = HandoverStatus.ACKNOWLEDGED
        db.commit()
        db.refresh(handover)

    agency = db.get(UserAgency, user.scope_user_agency_id)
    return _handover_out(handover, agency.name if agency else None)


@router.post("/assets/{work_id}/checkins", response_model=CheckinOut, status_code=201, tags=["lifecycle"])
def log_checkin(
    work_id: str,
    payload: CheckinRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Role.USER_AGENCY)),
) -> CheckinOut:
    """Record that the asset is still standing and still in use."""
    handover = db.scalar(
        select(AssetHandover).where(
            AssetHandover.work_id == work_id,
            AssetHandover.user_agency_id == user.scope_user_agency_id,
        )
    )
    if handover is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such asset.")

    checkin = LifecycleCheckin(
        work_id=work_id,
        checkin_date=REFERENCE_DATE,
        photo_reference=payload.photo_reference,
        still_in_use=payload.still_in_use,
        notes=payload.notes or None,
    )
    db.add(checkin)
    db.commit()
    db.refresh(checkin)
    return CheckinOut.model_validate(checkin)


@router.post(
    "/assets/{work_id}/maintenance",
    response_model=MaintenanceOut,
    status_code=201,
    tags=["lifecycle"],
)
def raise_maintenance(
    work_id: str,
    payload: MaintenanceRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Role.USER_AGENCY)),
) -> MaintenanceOut:
    """Raise a maintenance need for the asset.

    Not a request for MPLADS funds — the Scheme cannot pay for maintenance. This
    puts the need on record where the District Authority can see it and route it
    to the department whose budget covers upkeep.
    """
    handover = db.scalar(
        select(AssetHandover).where(
            AssetHandover.work_id == work_id,
            AssetHandover.user_agency_id == user.scope_user_agency_id,
        )
    )
    if handover is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such asset.")

    rec = MaintenanceRecommendation(
        work_id=work_id,
        user_agency_id=user.scope_user_agency_id,
        raised_date=REFERENCE_DATE,
        description=payload.description,
        photo_reference=payload.photo_reference,
        status="OPEN",
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return MaintenanceOut.model_validate(rec)


@router.get("/handovers/queue", response_model=list[dict], tags=["lifecycle"])
def handover_queue(
    db: Session = Depends(get_db),
    sc: Scope = Depends(scope),
    user: CurrentUser = Depends(
        require_roles(Role.DISTRICT_AUTHORITY, Role.STATE_NODAL, Role.MINISTRY)
    ),
) -> list[dict]:
    """Completed works whose handover has not been recorded or acknowledged."""
    completed = sc.works(
        select(Work).where(
            Work.status == WorkStatus.COMPLETED,
            Work.actual_completion_date.is_not(None),
        )
    )
    works = db.scalars(completed).all()
    handovers = {
        h.work_id: h
        for h in db.scalars(
            select(AssetHandover).where(AssetHandover.work_id.in_([w.work_id for w in works]))
        )
    }

    out = []
    for w in works:
        h = handovers.get(w.work_id)
        days = (REFERENCE_DATE - w.actual_completion_date).days
        if h is not None and h.handover_acknowledged_date is not None:
            continue
        if days <= 30:
            continue
        out.append(
            {
                "work_id": w.work_id,
                "work_type": w.work_type,
                "block": w.block,
                "district_id": w.district_id,
                "completed_on": w.actual_completion_date,
                "days_since_completion": days,
                "handover_state": "not initiated" if h is None else "awaiting acknowledgement",
                "uc_on_file": bool(h and h.uc_submitted_date),
                "register_entry": bool(h and h.register_entry_date),
            }
        )
    return sorted(out, key=lambda r: -r["days_since_completion"])


@router.get("/maintenance", response_model=list[MaintenanceOut], tags=["lifecycle"])
def list_maintenance(
    db: Session = Depends(get_db),
    sc: Scope = Depends(scope),
    user: CurrentUser = Depends(
        require_roles(Role.DISTRICT_AUTHORITY, Role.STATE_NODAL, Role.MINISTRY, Role.USER_AGENCY)
    ),
) -> list[MaintenanceOut]:
    visible = sc.works(select(Work.work_id))
    rows = db.scalars(
        select(MaintenanceRecommendation)
        .where(MaintenanceRecommendation.work_id.in_(visible))
        .order_by(MaintenanceRecommendation.raised_date.desc())
    ).all()
    return [MaintenanceOut.model_validate(r) for r in rows]
