"""Health, identity, reference data, and engine configuration."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, auth_mode, current_user, require_roles
from app.config.settings import settings
from app.db import get_db
from app.engine.engine_config import load_config
from app.engine.similarity import backend as similarity_backend
from app.models import Agency, District, UserAgency, Work
from app.models.enums import Role
from app.models.risk import EngineConfig

router = APIRouter()

DATA_NOTICE = "Synthetic demonstration data — not live MPLADS records"


@router.get("/health", tags=["system"])
def health(db: Session = Depends(get_db)) -> dict:
    works = db.scalar(select(func.count()).select_from(Work)) or 0
    return {
        "status": "ok",
        "engine_version": settings.engine_version,
        "db_backend": settings.db_backend,
        "auth": auth_mode(),
        "works_loaded": works,
        "data_notice": DATA_NOTICE,
    }


@router.get("/me", tags=["system"])
def me(user: CurrentUser = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """Who the caller is and what they may see, as the server understands it.

    The client renders navigation from this rather than from anything it decides
    for itself, so the interface and the access rules cannot drift apart.
    """
    scope_label = {
        Role.DISTRICT_AUTHORITY: "district",
        Role.STATE_NODAL: "state",
        Role.MP: "own recommendations",
        Role.IMPLEMENTING_AGENCY: "assigned works",
        Role.USER_AGENCY: "assets handed over",
        Role.MINISTRY: "national",
        Role.PUBLIC: "aggregates only",
    }[user.role]

    district = db.get(District, user.scope_district_id) if user.scope_district_id else None
    agency = db.get(Agency, user.scope_agency_id) if user.scope_agency_id else None
    user_agency = (
        db.get(UserAgency, user.scope_user_agency_id) if user.scope_user_agency_id else None
    )

    return {
        "user_id": user.user_id,
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role.value,
        "scope": scope_label,
        "scope_state": user.scope_state,
        "scope_district_id": user.scope_district_id,
        "scope_district_name": district.name if district else None,
        "scope_mp_id": user.scope_mp_id,
        "scope_agency_id": user.scope_agency_id,
        "scope_agency_name": agency.name if agency else None,
        "scope_user_agency_id": user.scope_user_agency_id,
        "scope_user_agency_name": user_agency.name if user_agency else None,
        "data_notice": DATA_NOTICE,
    }


@router.get("/reference/districts", tags=["system"])
def list_districts(db: Session = Depends(get_db)) -> list[dict]:
    return [
        {
            "district_id": d.district_id,
            "name": d.name,
            "state": d.state,
            "terrain_category": d.terrain_category.value,
            "centroid_lat": d.centroid_lat,
            "centroid_lon": d.centroid_lon,
        }
        for d in db.scalars(select(District).order_by(District.state, District.name))
    ]


@router.get("/reference/agencies", tags=["system"])
def list_agencies(db: Session = Depends(get_db), district: str | None = None) -> list[dict]:
    stmt = select(Agency)
    if district:
        stmt = stmt.where(Agency.district_id == district)
    return [
        {
            "agency_id": a.agency_id,
            "name": a.name,
            "agency_type": a.agency_type.value,
            "district_id": a.district_id,
        }
        for a in db.scalars(stmt.order_by(Agency.name))
    ]


@router.get("/engine/weights", tags=["system"])
def get_weights(db: Session = Depends(get_db), user: CurrentUser = Depends(current_user)) -> dict:
    """Current scoring configuration, and where the numbers came from."""
    config = load_config(db)
    return {
        "engine_version": config.engine_version,
        "stage1": config.stage1,
        "stage2": config.stage2,
        "stage3": config.stage3,
        "tiers": config.tiers,
        "thresholds": config.thresholds,
        "caps": config.caps,
        "similarity_backend": similarity_backend(),
        "notes": {
            "agency_cap": (
                "The AGENCY module's contribution is clamped at 15% of the composite in "
                "scoring.py regardless of the weight set here, so retuning cannot make an "
                "agency's historical record decisive."
            ),
            "compliance_override": (
                "Any COMPLIANCE finding lifts the work to at least HIGH. A broken rule is a "
                "determinate fact, not a statistical inference."
            ),
            "stage2_compliance": (
                "Two compliance checks apply after sanction. They carry no weight at Stage 2 "
                "and act only through the tier override, so the Stage 2 weights stay as "
                "specified."
            ),
        },
    }


@router.put("/engine/weights", tags=["system"])
def update_weights(
    payload: dict,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Role.MINISTRY)),
) -> dict:
    """Retune thresholds and weights. Takes effect on the next scoring run.

    Writes to ``engine_config``; ``weights.yaml`` stays as the documented default
    and the value a reset returns to. Every change records who made it.
    """
    allowed_scopes = {"stage1", "stage2", "stage3", "tiers", "thresholds", "caps"}
    changed = 0

    for scope_name, entries in payload.items():
        if scope_name not in allowed_scopes or not isinstance(entries, dict):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"Unknown configuration section {scope_name!r}.",
            )
        for key, value in entries.items():
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    f"{scope_name}.{key} must be a number.",
                ) from None

            row = db.scalar(
                select(EngineConfig).where(
                    EngineConfig.scope == scope_name, EngineConfig.key == key
                )
            )
            if row is None:
                row = EngineConfig(scope=scope_name, key=key, value=numeric)
                db.add(row)
            else:
                row.value = numeric
            row.updated_at = datetime.utcnow()
            row.updated_by = user.display_name
            changed += 1

    db.commit()
    config = load_config(db)
    return {
        "updated": changed,
        "updated_by": user.display_name,
        "engine_version": config.engine_version,
        "note": (
            "Existing assessments keep the scores they were computed with. Re-run screening "
            "to apply the new configuration."
        ),
    }
