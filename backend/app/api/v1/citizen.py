"""Citizen submissions — a suggestion or a concern from a member of the public.

The public MPLADS portal lets a citizen put a work forward for their Member's
consideration, or raise something about a work already under way. This is that,
with the constraint that matters made explicit:

**A submission is never a work.** Under the Scheme only a Member of Parliament
may recommend a work. Writing public input into ``works`` would let an
unauthenticated form feed the screening pipeline and sit alongside sanctioned
records. A submission is correspondence: it reaches the Member and the District
Authority, and stops there. Nothing here is screened, scored, or able to change
the state of an existing work.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, Scope, require_roles, scope
from app.db import get_db
from app.models import CitizenSubmission, District, Work
from app.models.enums import Role, SubmissionStatus, SubmissionType

router = APIRouter()

# A crude ceiling on an unauthenticated endpoint. Real deployment would want
# rate limiting and a captcha in front of this; the length caps at least stop a
# single request carrying an unbounded payload.
MAX_DESCRIPTION = 1200


class SubmissionRequest(BaseModel):
    submission_type: SubmissionType
    district_id: str
    block: str | None = Field(default=None, max_length=80)
    related_work_id: str | None = None
    suggested_work_type: str | None = Field(default=None, max_length=48)
    description: str = Field(min_length=25, max_length=MAX_DESCRIPTION)
    submitter_name: str = Field(min_length=2, max_length=120)
    #: Optional on purpose — a citizen should be able to raise something without
    #: having to leave a way of being contacted about it.
    submitter_contact: str | None = Field(default=None, max_length=160)

    @field_validator("description", "submitter_name")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class SubmissionOut(BaseModel):
    submission_id: int
    submission_type: str
    district_id: str
    district_name: str | None = None
    block: str | None
    related_work_id: str | None
    suggested_work_type: str | None
    description: str
    submitter_name: str
    submitted_at: datetime
    status: str
    official_response: str | None
    responded_by: str | None


class SubmissionReceipt(BaseModel):
    """What the citizen is told, and deliberately no more.

    It confirms the submission was recorded and says what happens next. It does
    not promise an outcome, because the system has no authority to deliver one.
    """

    submission_id: int
    reference: str
    status: str
    message: str


class RespondRequest(BaseModel):
    response: str = Field(min_length=10, max_length=1200)
    close: bool = False


@router.post(
    "/public/submissions",
    response_model=SubmissionReceipt,
    status_code=status.HTTP_201_CREATED,
    tags=["public"],
)
def create_submission(payload: SubmissionRequest, db: Session = Depends(get_db)) -> SubmissionReceipt:
    """Accept a suggestion or a concern. No sign-in required."""
    district = db.get(District, payload.district_id)
    if district is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown district.")

    if payload.related_work_id is not None:
        work = db.get(Work, payload.related_work_id)
        if work is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "No work with that reference. Leave it blank if you are not sure.",
            )
        if work.district_id != payload.district_id:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "That work is not in the district selected.",
            )

    row = CitizenSubmission(
        submission_type=payload.submission_type.value,
        district_id=payload.district_id,
        block=payload.block,
        related_work_id=payload.related_work_id,
        suggested_work_type=payload.suggested_work_type,
        description=payload.description,
        submitter_name=payload.submitter_name,
        submitter_contact=payload.submitter_contact or None,
        status=SubmissionStatus.RECEIVED.value,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    reference = f"CS-{row.submission_id:06d}"
    is_suggestion = payload.submission_type is SubmissionType.WORK_SUGGESTION
    message = (
        (
            "Your suggestion has been recorded and will reach the Member for this constituency "
            "and the District Authority. A suggestion is not a sanctioned work: only a Member of "
            "Parliament may recommend one, and only the District Authority may sanction it."
        )
        if is_suggestion
        else (
            "Your concern has been recorded and will reach the District Authority for this "
            "district. It does not change the status of the work, and it is not a finding — a "
            "person will read it and decide what it warrants."
        )
    )

    return SubmissionReceipt(
        submission_id=row.submission_id,
        reference=reference,
        status=row.status,
        message=f"{message} Quote {reference} in any follow-up.",
    )


@router.get("/submissions", response_model=list[SubmissionOut], tags=["public"])
def list_submissions(
    db: Session = Depends(get_db),
    sc: Scope = Depends(scope),
    user: CurrentUser = Depends(
        require_roles(Role.DISTRICT_AUTHORITY, Role.STATE_NODAL, Role.MINISTRY, Role.MP)
    ),
    submission_type: SubmissionType | None = None,
    status_filter: SubmissionStatus | None = None,
) -> list[SubmissionOut]:
    """Submissions an official may see, scoped the same way works are.

    A Member sees submissions for the districts they represent; a District
    Authority sees its own district. The contact details a citizen chose to leave
    are not returned here — an official needs the substance, and the address only
    matters at the point of replying.
    """
    stmt = select(CitizenSubmission)

    if user.role is Role.DISTRICT_AUTHORITY:
        stmt = stmt.where(CitizenSubmission.district_id == user.scope_district_id)
    elif user.role is Role.STATE_NODAL:
        stmt = stmt.where(
            CitizenSubmission.district_id.in_(
                select(District.district_id).where(District.state == user.scope_state)
            )
        )
    elif user.role is Role.MP:
        # A Member sees submissions from districts they have worked in.
        stmt = stmt.where(
            CitizenSubmission.district_id.in_(
                select(Work.district_id).where(Work.mp_id == user.scope_mp_id).distinct()
            )
        )

    if submission_type:
        stmt = stmt.where(CitizenSubmission.submission_type == submission_type.value)
    if status_filter:
        stmt = stmt.where(CitizenSubmission.status == status_filter.value)

    rows = db.scalars(stmt.order_by(CitizenSubmission.submitted_at.desc()).limit(200)).all()
    names = dict(db.execute(select(District.district_id, District.name)).all())

    return [
        SubmissionOut(
            submission_id=r.submission_id,
            submission_type=r.submission_type,
            district_id=r.district_id,
            district_name=names.get(r.district_id),
            block=r.block,
            related_work_id=r.related_work_id,
            suggested_work_type=r.suggested_work_type,
            description=r.description,
            submitter_name=r.submitter_name,
            submitted_at=r.submitted_at,
            status=r.status,
            official_response=r.official_response,
            responded_by=r.responded_by,
        )
        for r in rows
    ]


@router.post("/submissions/{submission_id}/respond", response_model=SubmissionOut, tags=["public"])
def respond_to_submission(
    submission_id: int,
    payload: RespondRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Role.DISTRICT_AUTHORITY, Role.MINISTRY)),
) -> SubmissionOut:
    """Record an official reply. Acknowledging is not agreeing."""
    row = db.get(CitizenSubmission, submission_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such submission.")
    if user.role is Role.DISTRICT_AUTHORITY and row.district_id != user.scope_district_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such submission.")

    row.official_response = payload.response.strip()
    row.responded_by = user.display_name
    row.status = (
        SubmissionStatus.CLOSED.value if payload.close else SubmissionStatus.ACKNOWLEDGED.value
    )
    db.commit()
    db.refresh(row)

    district = db.get(District, row.district_id)
    return SubmissionOut(
        submission_id=row.submission_id,
        submission_type=row.submission_type,
        district_id=row.district_id,
        district_name=district.name if district else None,
        block=row.block,
        related_work_id=row.related_work_id,
        suggested_work_type=row.suggested_work_type,
        description=row.description,
        submitter_name=row.submitter_name,
        submitted_at=row.submitted_at,
        status=row.status,
        official_response=row.official_response,
        responded_by=row.responded_by,
    )
