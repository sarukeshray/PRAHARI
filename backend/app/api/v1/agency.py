"""What an implementing agency submits: progress, photographs, and responses.

**The photograph endpoint is where the geotag module's integrity actually lives.**
The file is uploaded to the server and the GPS and capture time are extracted
here, from the image itself, with Pillow. They are never accepted from the
client. The party uploading the photograph is exactly the party the geotag check
exists to verify, so trusting their copy of the metadata would leave no control
at all — the check would only catch someone who forgot to lie.

Storage is the local filesystem. Firebase Storage is a drop-in replacement for
`_store_file` when a project is configured; nothing else would change.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, require_roles
from app.config.settings import BACKEND_ROOT
from app.db import get_db
from app.models import Agency, CompletionPhoto, ProgressReport, Work
from app.models.enums import PhotoStage, Role, WorkStatus
from app.models.risk import AgencyResponse, RiskFlag

router = APIRouter()

UPLOAD_ROOT = BACKEND_ROOT / "data" / "uploads"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _own_work(db: Session, work_id: str, user: CurrentUser) -> Work:
    work = db.get(Work, work_id)
    if work is None or work.agency_id != user.scope_agency_id:
        # 404 rather than 403: confirming the work exists would tell an agency
        # something about works it is not executing.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such work assigned to this agency.")
    return work


# ---------------------------------------------------------------------------
# Progress reports
# ---------------------------------------------------------------------------


class ProgressRequest(BaseModel):
    physical_progress_pct: float = Field(ge=0, le=100)
    remarks: str = Field(default="", max_length=600)


class ProgressOut(BaseModel):
    report_id: int
    work_id: str
    report_date: date
    physical_progress_pct: float
    remarks: str | None


@router.post("/agency/works/{work_id}/progress", response_model=ProgressOut, status_code=201, tags=["agency"])
def submit_progress(
    work_id: str,
    payload: ProgressRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Role.IMPLEMENTING_AGENCY)),
) -> ProgressOut:
    """File physical progress — one half of the comparison the engine makes.

    The figure is the agency's own claim. That is the point: the disbursement
    module compares it against money actually released, and a gap between them is
    what the finding is about.
    """
    work = _own_work(db, work_id, user)
    if work.sanctioned_date is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "This work has not been sanctioned, so there is no progress to report against it.",
        )

    row = ProgressReport(
        work_id=work_id,
        report_date=date.today(),
        physical_progress_pct=payload.physical_progress_pct,
        remarks=payload.remarks.strip() or None,
    )
    db.add(row)

    if payload.physical_progress_pct >= 100 and work.status != WorkStatus.COMPLETED:
        work.status = WorkStatus.COMPLETED
        work.actual_completion_date = date.today()

    db.commit()
    db.refresh(row)
    return ProgressOut(
        report_id=row.report_id,
        work_id=row.work_id,
        report_date=row.report_date,
        physical_progress_pct=row.physical_progress_pct,
        remarks=row.remarks,
    )


# ---------------------------------------------------------------------------
# Photographs
# ---------------------------------------------------------------------------


class PhotoOut(BaseModel):
    photo_id: int
    work_id: str
    stage: str
    upload_date: date
    capture_timestamp: datetime | None
    photo_lat: float | None
    photo_lon: float | None
    image_hash: str
    #: What the server could and could not read out of the file, stated plainly
    #: so an agency is not left guessing why a finding did or did not appear.
    metadata_note: str


def _dms_to_degrees(value, ref: str | None) -> float | None:
    """Convert EXIF degrees/minutes/seconds to a signed decimal degree."""
    try:
        d, m, s = (float(x) for x in value)
    except (TypeError, ValueError):
        return None
    result = d + m / 60 + s / 3600
    if ref in {"S", "W"}:
        result = -result
    return round(result, 6)


def _extract_exif(data: bytes) -> tuple[datetime | None, float | None, float | None, str]:
    """Read capture time and GPS out of the image itself.

    Returns a note alongside the values, because "no GPS in this photograph" and
    "GPS 6 km away" are very different things for a reviewer and should not both
    surface as silence.
    """
    try:
        import io

        from PIL import ExifTags, Image
    except Exception:  # noqa: BLE001
        return None, None, None, "Image library unavailable; metadata not read."

    try:
        image = Image.open(io.BytesIO(data))
        exif = image.getexif()
    except Exception:  # noqa: BLE001
        return None, None, None, "File could not be opened as an image."

    if not exif:
        return None, None, None, "No EXIF metadata present in this photograph."

    tags = {ExifTags.TAGS.get(k, k): v for k, v in exif.items()}

    captured = None
    raw_time = tags.get("DateTimeOriginal") or tags.get("DateTime")
    if isinstance(raw_time, str):
        try:
            captured = datetime.strptime(raw_time, "%Y:%m:%d %H:%M:%S")
        except ValueError:
            captured = None

    lat = lon = None
    try:
        gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
    except Exception:  # noqa: BLE001
        gps = None
    if gps:
        gps_tags = {ExifTags.GPSTAGS.get(k, k): v for k, v in gps.items()}
        lat = _dms_to_degrees(gps_tags.get("GPSLatitude"), gps_tags.get("GPSLatitudeRef"))
        lon = _dms_to_degrees(gps_tags.get("GPSLongitude"), gps_tags.get("GPSLongitudeRef"))

    parts = []
    parts.append(
        f"Capture time read as {captured:%d %b %Y %H:%M}." if captured else "No capture time in EXIF."
    )
    parts.append(
        f"GPS read as {lat}, {lon}." if lat is not None and lon is not None else "No GPS in EXIF."
    )
    return captured, lat, lon, " ".join(parts)


def _store_file(work_id: str, filename: str, data: bytes) -> str:
    """Write the file and return a reference.

    Swapping this for Firebase Storage is the only change needed to move uploads
    off the local disk.
    """
    folder = UPLOAD_ROOT / work_id
    folder.mkdir(parents=True, exist_ok=True)
    suffix = Path(filename).suffix.lower() or ".jpg"
    digest = hashlib.sha256(data).hexdigest()[:16]
    path = folder / f"{digest}{suffix}"
    path.write_bytes(data)
    return f"uploads/{work_id}/{path.name}"


@router.post("/agency/works/{work_id}/photos", response_model=PhotoOut, status_code=201, tags=["agency"])
async def upload_photo(
    work_id: str,
    stage: PhotoStage = Form(default=PhotoStage.COMPLETE),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Role.IMPLEMENTING_AGENCY)),
) -> PhotoOut:
    """Upload a site photograph. Location and time come from the file, not the form."""
    work = _own_work(db, work_id, user)

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Upload a JPEG, PNG or WebP image. This file is {file.content_type or 'of unknown type'}.",
        )

    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"Photographs must be under {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
        )
    if not data:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "The file is empty.")

    captured, lat, lon, note = _extract_exif(data)
    reference = _store_file(work_id, file.filename or "photo.jpg", data)

    row = CompletionPhoto(
        work_id=work_id,
        upload_date=date.today(),
        capture_timestamp=captured,
        photo_lat=lat,
        photo_lon=lon,
        stage=stage,
        # A content hash, so the same file submitted against two works is
        # detectable however it was renamed.
        image_hash=hashlib.sha256(data).hexdigest()[:32],
        storage_path=reference,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return PhotoOut(
        photo_id=row.photo_id,
        work_id=row.work_id,
        stage=row.stage.value,
        upload_date=row.upload_date,
        capture_timestamp=row.capture_timestamp,
        photo_lat=row.photo_lat,
        photo_lon=row.photo_lon,
        image_hash=row.image_hash,
        metadata_note=(
            f"{note} Read on the server from the file itself, never from the browser — the "
            f"geotag check exists to verify the uploader."
        ),
    )


# ---------------------------------------------------------------------------
# Responses to findings
# ---------------------------------------------------------------------------


class AgencyResponseRequest(BaseModel):
    note: str = Field(min_length=15, max_length=1200)
    evidence_reference: str | None = Field(default=None, max_length=512)


class AgencyResponseOut(BaseModel):
    response_id: int
    flag_id: int
    submitted_date: date
    note: str
    evidence_reference: str | None
    flag_status: str


@router.post("/agency/flags/{flag_id}/respond", response_model=AgencyResponseOut, status_code=201, tags=["agency"])
def respond_to_flag(
    flag_id: int,
    payload: AgencyResponseRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Role.IMPLEMENTING_AGENCY)),
) -> AgencyResponseOut:
    """Attach the agency's account of a finding.

    **A response never clears a finding.** It goes back to the District Authority
    as evidence for a person to weigh. Letting the party a finding is about
    resolve it would empty the review workflow of meaning, so the flag's status
    is deliberately untouched here.
    """
    flag = db.get(RiskFlag, flag_id)
    if flag is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such finding.")
    _own_work(db, flag.work_id, user)

    row = AgencyResponse(
        flag_id=flag_id,
        agency_id=user.scope_agency_id,
        submitted_date=date.today(),
        note=payload.note.strip(),
        evidence_reference=payload.evidence_reference,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return AgencyResponseOut(
        response_id=row.response_id,
        flag_id=row.flag_id,
        submitted_date=row.submitted_date,
        note=row.note,
        evidence_reference=row.evidence_reference,
        flag_status=flag.status.value,
    )


@router.get("/agency/flags/{flag_id}/responses", response_model=list[AgencyResponseOut], tags=["agency"])
def list_responses(
    flag_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(
        require_roles(Role.IMPLEMENTING_AGENCY, Role.DISTRICT_AUTHORITY, Role.MINISTRY)
    ),
) -> list[AgencyResponseOut]:
    flag = db.get(RiskFlag, flag_id)
    if flag is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such finding.")
    if user.role is Role.IMPLEMENTING_AGENCY:
        _own_work(db, flag.work_id, user)

    rows = db.scalars(
        select(AgencyResponse)
        .where(AgencyResponse.flag_id == flag_id)
        .order_by(AgencyResponse.submitted_date.desc())
    ).all()
    return [
        AgencyResponseOut(
            response_id=r.response_id,
            flag_id=r.flag_id,
            submitted_date=r.submitted_date,
            note=r.note,
            evidence_reference=r.evidence_reference,
            flag_status=flag.status.value,
        )
        for r in rows
    ]
