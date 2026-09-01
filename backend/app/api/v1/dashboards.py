"""Dashboard aggregates, one shape per role.

Each endpoint answers the question that role actually has. A District Officer
asks "what needs me today"; a Ministry analyst asks "which state is struggling";
a citizen asks "was the money spent and did the work finish". They are different
questions, so they are different endpoints rather than one filtered by role.
"""

from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, Scope, current_user, require_roles, scope
from app.db import get_db
from app.engine.context import REFERENCE_DATE, build_context, financial_year_of
from app.engine.stage3 import handover as handover_module
from app.models import MP, Agency, District, Payment, Work
from app.models.enums import FlagStatus, HandoverStatus, Role, SeverityTier, WorkStatus
from app.models.risk import RiskAssessment, RiskFlag
from app.schemas.api import (
    AgencyPerformance,
    DistrictSummary,
    ModuleCount,
    PublicAggregate,
    TierCounts,
    TrendPoint,
)

router = APIRouter()


def _tier_counts(db: Session, work_ids_stmt) -> TierCounts:
    """Most severe current tier per work, counted."""
    rows = db.execute(
        select(RiskAssessment.work_id, RiskAssessment.severity_tier).where(
            RiskAssessment.work_id.in_(work_ids_stmt)
        )
    ).all()
    rank = {SeverityTier.CRITICAL: 0, SeverityTier.HIGH: 1, SeverityTier.MEDIUM: 2, SeverityTier.LOW: 3}
    best: dict[str, SeverityTier] = {}
    for work_id, tier in rows:
        held = best.get(work_id)
        if held is None or rank[tier] < rank[held]:
            best[work_id] = tier
    counts = TierCounts()
    for tier in best.values():
        setattr(counts, tier.value, getattr(counts, tier.value) + 1)
    return counts


@router.get("/dashboard/district/{district_id}/summary", response_model=DistrictSummary, tags=["dashboards"])
def district_summary(
    district_id: str,
    db: Session = Depends(get_db),
    sc: Scope = Depends(scope),
) -> DistrictSummary:
    district = db.get(District, district_id)
    if district is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such district.")

    # Narrowed by scope, so a caller asking about someone else's district gets
    # an empty summary rather than a different error - the shape of the reply
    # does not tell them whether the district has anything in it.
    visible = sc.works(select(Work.work_id).where(Work.district_id == district_id))
    in_district = db.scalar(select(func.count()).select_from(visible.subquery())) or 0

    open_findings = db.scalar(
        select(func.count())
        .select_from(RiskFlag)
        .where(RiskFlag.work_id.in_(visible), RiskFlag.status == FlagStatus.OPEN)
    ) or 0

    by_module = [
        ModuleCount(module=module, count=count)
        for module, count in db.execute(
            select(RiskFlag.module, func.count())
            .where(RiskFlag.work_id.in_(visible), RiskFlag.status == FlagStatus.OPEN)
            .group_by(RiskFlag.module)
            .order_by(func.count().desc())
        ).all()
    ]

    # Findings per month, from the recommendation date of the work they sit on.
    trend_rows = db.execute(
        select(
            func.strftime("%Y-%m", Work.recommended_date),
            func.count(RiskFlag.flag_id),
        )
        .select_from(RiskFlag)
        .join(Work, Work.work_id == RiskFlag.work_id)
        .where(RiskFlag.work_id.in_(visible), Work.recommended_date.is_not(None))
        .group_by(func.strftime("%Y-%m", Work.recommended_date))
        .order_by(func.strftime("%Y-%m", Work.recommended_date))
    ).all()
    trend = [TrendPoint(period=p, count=c) for p, c in trend_rows if p][-18:]

    overdue = db.scalar(
        select(func.count())
        .select_from(RiskFlag)
        .where(
            RiskFlag.work_id.in_(visible),
            RiskFlag.flag_code == "HANDOVER_OVERDUE",
            RiskFlag.status == FlagStatus.OPEN,
        )
    ) or 0

    return DistrictSummary(
        district_id=district.district_id,
        district_name=district.name,
        state=district.state,
        works_total=in_district,
        works_screened=db.scalar(
            select(func.count(func.distinct(RiskAssessment.work_id))).where(
                RiskAssessment.work_id.in_(visible)
            )
        ) or 0,
        open_findings=open_findings,
        tier_counts=_tier_counts(db, visible),
        by_module=by_module,
        trend=trend,
        handover_overdue=overdue,
    )


@router.get("/dashboard/district/{district_id}/map", tags=["dashboards"])
def district_map(
    district_id: str,
    db: Session = Depends(get_db),
    sc: Scope = Depends(scope),
    only_findings: bool = False,
) -> dict:
    """GeoJSON FeatureCollection of works, coloured by tier on the client."""
    stmt = sc.works(select(Work).where(Work.district_id == district_id))
    works = db.scalars(stmt).all()

    rank = {SeverityTier.CRITICAL: 0, SeverityTier.HIGH: 1, SeverityTier.MEDIUM: 2, SeverityTier.LOW: 3}
    tiers: dict[str, SeverityTier] = {}
    explanations: dict[str, str] = {}
    for work_id, tier in db.execute(
        select(RiskAssessment.work_id, RiskAssessment.severity_tier).where(
            RiskAssessment.work_id.in_([w.work_id for w in works])
        )
    ).all():
        held = tiers.get(work_id)
        if held is None or rank[tier] < rank[held]:
            tiers[work_id] = tier
    for work_id, explanation in db.execute(
        select(RiskFlag.work_id, RiskFlag.explanation).where(
            RiskFlag.work_id.in_([w.work_id for w in works]),
            RiskFlag.status == FlagStatus.OPEN,
        )
    ).all():
        explanations.setdefault(work_id, explanation)

    features = []
    for w in works:
        tier = tiers.get(w.work_id)
        if only_findings and w.work_id not in explanations:
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [w.longitude, w.latitude]},
                "properties": {
                    "work_id": w.work_id,
                    "work_type": w.work_type,
                    "block": w.block,
                    "estimated_cost": w.estimated_cost,
                    "status": w.status.value,
                    "severity_tier": tier.value if tier else None,
                    "primary_finding": explanations.get(w.work_id),
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


@router.get("/dashboard/state/{state}/districts", tags=["dashboards"])
def state_districts(
    state: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Role.STATE_NODAL, Role.MINISTRY)),
    sc: Scope = Depends(scope),
) -> list[dict]:
    """One row per district: flag rate against resolution time.

    Lets a State officer find the district that is both slow and high-risk, which
    neither number identifies on its own.
    """
    if user.role is Role.STATE_NODAL and user.scope_state != state:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Outside your state.")

    districts = db.scalars(select(District).where(District.state == state)).all()
    out = []
    for d in districts:
        work_ids = select(Work.work_id).where(Work.district_id == d.district_id)
        total = db.scalar(select(func.count()).select_from(work_ids.subquery())) or 0
        open_flags = db.scalar(
            select(func.count())
            .select_from(RiskFlag)
            .where(RiskFlag.work_id.in_(work_ids), RiskFlag.status == FlagStatus.OPEN)
        ) or 0
        resolved = db.scalar(
            select(func.count())
            .select_from(RiskFlag)
            .where(RiskFlag.work_id.in_(work_ids), RiskFlag.status != FlagStatus.OPEN)
        ) or 0
        out.append(
            {
                "district_id": d.district_id,
                "district_name": d.name,
                "terrain_category": d.terrain_category.value,
                "works": total,
                "open_findings": open_flags,
                "resolved_findings": resolved,
                "flag_rate_pct": round(open_flags / total * 100, 1) if total else 0.0,
                "resolution_rate_pct": round(
                    resolved / (resolved + open_flags) * 100, 1
                ) if (resolved + open_flags) else 0.0,
            }
        )
    return out


@router.get("/dashboard/national", tags=["dashboards"])
def national_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Role.MINISTRY)),
) -> dict:
    states = db.scalars(select(District.state).distinct()).all()
    rows = []
    for state in states:
        work_ids = select(Work.work_id).where(
            Work.district_id.in_(select(District.district_id).where(District.state == state))
        )
        total = db.scalar(select(func.count()).select_from(work_ids.subquery())) or 0
        sanctioned = db.scalar(
            select(func.coalesce(func.sum(Work.estimated_cost), 0.0)).where(
                Work.work_id.in_(work_ids), Work.sanctioned_date.is_not(None)
            )
        ) or 0.0
        disbursed = db.scalar(
            select(func.coalesce(func.sum(Payment.amount), 0.0)).where(
                Payment.work_id.in_(work_ids)
            )
        ) or 0.0
        critical = db.scalar(
            select(func.count())
            .select_from(RiskFlag)
            .where(
                RiskFlag.work_id.in_(work_ids),
                RiskFlag.status == FlagStatus.OPEN,
                RiskFlag.severity_tier == SeverityTier.CRITICAL,
            )
        ) or 0
        high = db.scalar(
            select(func.count())
            .select_from(RiskFlag)
            .where(
                RiskFlag.work_id.in_(work_ids),
                RiskFlag.status == FlagStatus.OPEN,
                RiskFlag.severity_tier == SeverityTier.HIGH,
            )
        ) or 0
        rows.append(
            {
                "state": state,
                "works": total,
                "sanctioned_amount": sanctioned,
                "disbursed_amount": disbursed,
                "utilisation_pct": round(disbursed / sanctioned * 100, 1) if sanctioned else 0.0,
                "open_critical": critical,
                "open_high": high,
            }
        )

    return {
        "states": sorted(rows, key=lambda r: -r["open_critical"]),
        "totals": {
            "works": db.scalar(select(func.count()).select_from(Work)) or 0,
            "open_findings": db.scalar(
                select(func.count()).select_from(RiskFlag).where(RiskFlag.status == FlagStatus.OPEN)
            ) or 0,
            "unresolved_critical": db.scalar(
                select(func.count())
                .select_from(RiskFlag)
                .where(
                    RiskFlag.status == FlagStatus.OPEN,
                    RiskFlag.severity_tier == SeverityTier.CRITICAL,
                )
            ) or 0,
            "districts": db.scalar(select(func.count()).select_from(District)) or 0,
        },
    }


@router.get("/dashboard/mp/summary", tags=["dashboards"])
def mp_summary(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Role.MP)),
) -> dict:
    """Entitlement and mandated-area position for the signed-in Member."""
    mp = db.get(MP, user.scope_mp_id)
    if mp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No member record.")

    works = db.scalars(select(Work).where(Work.mp_id == mp.mp_id)).all()
    current_fy = financial_year_of(REFERENCE_DATE)
    this_year = [
        w for w in works if w.recommended_date and financial_year_of(w.recommended_date) == current_fy
    ]

    recommended = sum(w.estimated_cost for w in this_year)
    sanctioned = sum(w.estimated_cost for w in this_year if w.sanctioned_date)
    sc_st_value = sum(w.estimated_cost for w in this_year if w.is_sc_st_area)

    disbursed = db.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0.0)).where(
            Payment.work_id.in_([w.work_id for w in this_year] or [""])
        )
    ) or 0.0

    return {
        "mp_id": mp.mp_id,
        "name": mp.name,
        "house": mp.house.value,
        "constituency": mp.constituency,
        "state": mp.state,
        "financial_year": f"{current_fy}-{str(current_fy + 1)[2:]}",
        "entitlement": mp.annual_entitlement,
        "recommended": recommended,
        "sanctioned": sanctioned,
        "disbursed": disbursed,
        "utilisation_pct": round(recommended / mp.annual_entitlement * 100, 1),
        "works_recommended": len(this_year),
        "works_completed": sum(1 for w in works if w.status == WorkStatus.COMPLETED),
        "works_total_all_years": len(works),
        "sc_st_allocation_pct": round(sc_st_value / recommended * 100, 1) if recommended else 0.0,
        "sc_st_required_pct": 22.5,
        "sc_required_pct": 15.0,
        "st_required_pct": 7.5,
    }


@router.get("/public/aggregates", response_model=list[PublicAggregate], tags=["public"])
def public_aggregates(db: Session = Depends(get_db)) -> list[PublicAggregate]:
    """The only public endpoint, and deliberately the least interesting one.

    No authentication, and no work identifiers, agency names, member names or
    findings — by design, not by omission. A citizen may see how much was
    committed and how much finished. Everything an individual could be judged by
    stays behind a sign-in.
    """
    out = []
    for state in db.scalars(select(District.state).distinct()).all():
        work_ids = select(Work.work_id).where(
            Work.district_id.in_(select(District.district_id).where(District.state == state))
        )
        total = db.scalar(select(func.count()).select_from(work_ids.subquery())) or 0
        completed = db.scalar(
            select(func.count()).select_from(Work).where(
                Work.work_id.in_(work_ids), Work.status == WorkStatus.COMPLETED
            )
        ) or 0
        sanctioned = db.scalar(
            select(func.coalesce(func.sum(Work.estimated_cost), 0.0)).where(
                Work.work_id.in_(work_ids), Work.sanctioned_date.is_not(None)
            )
        ) or 0.0
        disbursed = db.scalar(
            select(func.coalesce(func.sum(Payment.amount), 0.0)).where(
                Payment.work_id.in_(work_ids)
            )
        ) or 0.0
        out.append(
            PublicAggregate(
                state=state,
                works_total=total,
                works_completed=completed,
                completion_rate_pct=round(completed / total * 100, 1) if total else 0.0,
                sanctioned_amount=sanctioned,
                disbursed_amount=disbursed,
                utilisation_pct=round(disbursed / sanctioned * 100, 1) if sanctioned else 0.0,
            )
        )
    return out


@router.get("/agencies/{agency_id}/performance", response_model=AgencyPerformance, tags=["agencies"])
def agency_performance(
    agency_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(current_user),
) -> AgencyPerformance:
    """An agency's record, always with the peer group it was measured against.

    The peer set is named in the response because a percentile without its
    comparison group is not interpretable, and because an agency is entitled to
    see how it is being measured.
    """
    if user.role is Role.IMPLEMENTING_AGENCY and user.scope_agency_id != agency_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only see your own record.")
    if user.role is Role.PUBLIC:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not available publicly.")

    agency = db.get(Agency, agency_id)
    if agency is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such agency.")

    ctx = build_context(db)
    stats = ctx.agency_stats.get(agency_id)
    if stats is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No completed works on record.")

    terrain = ctx.districts[agency.district_id].terrain_category
    peers = [
        s.percentile
        for aid, s in ctx.agency_stats.items()
        if aid in ctx.agencies
        and ctx.districts[ctx.agencies[aid].district_id].terrain_category is terrain
    ]

    floor = ctx.config.t("AGENCY_PERCENTILE_FLOOR")
    min_completed = ctx.config.t("AGENCY_MIN_COMPLETED_WORKS")
    flagged = stats.percentile < floor and stats.completed >= min_completed

    note = (
        f"Ranked against {stats.peer_count} agencies working in {terrain.value} districts, "
        f"never against a national average. This signal contributes at most 15% of a "
        f"pre-sanction score and is never a gate on its own."
    )
    if stats.completed < min_completed:
        note += (
            f" No finding is raised below {min_completed:.0f} completed works; this agency has "
            f"{stats.completed}."
        )

    return AgencyPerformance(
        agency_id=agency.agency_id,
        name=agency.name,
        terrain_category=terrain.value,
        percentile=round(stats.percentile, 1),
        peer_count=stats.peer_count,
        peer_group_label=f"{terrain.value.title()} districts",
        completed_works=stats.completed,
        total_works=stats.total,
        completion_rate=round(stats.completion_rate * 100, 1),
        mean_delay_days=round(stats.mean_delay_days, 1),
        mean_overrun_pct=round(stats.mean_overrun_pct, 1),
        peer_percentiles=sorted(round(p, 1) for p in peers),
        flagged=flagged,
        note=note,
    )
