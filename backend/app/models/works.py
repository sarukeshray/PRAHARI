"""Works and the records that accumulate against them once they are underway."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import PhotoStage, PlantedAnomaly, WorkStatus
from app.models.reference import Agency, District, UserAgency, enum_col


class Work(Base):
    __tablename__ = "works"

    work_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    mp_id: Mapped[str | None] = mapped_column(ForeignKey("mps.mp_id"), index=True, nullable=True)
    district_id: Mapped[str] = mapped_column(ForeignKey("districts.district_id"), index=True)
    block: Mapped[str] = mapped_column(String(80), index=True)
    panchayat: Mapped[str | None] = mapped_column(String(80), nullable=True)
    work_type: Mapped[str] = mapped_column(String(48), index=True)
    description: Mapped[str] = mapped_column(Text)

    estimated_cost: Mapped[float] = mapped_column(Float)
    final_cost: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Nullable so CAG-04 can be modelled: a sanction recorded against no
    # recommendation. The COMPLIANCE module raises MISSING_RECOMMENDATION on it.
    recommended_date: Mapped[date | None] = mapped_column(Date, index=True, nullable=True)
    sanctioned_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expected_completion_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_completion_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    status: Mapped[WorkStatus] = mapped_column(enum_col(WorkStatus), index=True)
    agency_id: Mapped[str | None] = mapped_column(
        ForeignKey("agencies.agency_id"), index=True, nullable=True
    )

    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    is_sc_st_area: Mapped[bool] = mapped_column(Boolean, default=False)

    # Evaluation label only. Never read by the engine, never sent to a reviewer.
    planted_anomaly: Mapped[PlantedAnomaly | None] = mapped_column(
        enum_col(PlantedAnomaly), nullable=True, index=True
    )

    # Cached sentence-transformer embedding for the duplicate module, so the
    # model runs once per description rather than once per comparison.
    description_embedding: Mapped[bytes | None] = mapped_column(nullable=True)

    mp: Mapped["MP | None"] = relationship(back_populates="works")  # noqa: F821
    district: Mapped[District] = relationship()
    agency: Mapped[Agency | None] = relationship()
    payments: Mapped[list["Payment"]] = relationship(back_populates="work", cascade="all, delete")
    progress_reports: Mapped[list["ProgressReport"]] = relationship(
        back_populates="work", cascade="all, delete"
    )
    photos: Mapped[list["CompletionPhoto"]] = relationship(
        back_populates="work", cascade="all, delete"
    )


class Payment(Base):
    __tablename__ = "payments"

    payment_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_id: Mapped[str] = mapped_column(ForeignKey("works.work_id"), index=True)
    installment_no: Mapped[int] = mapped_column(Integer)
    amount: Mapped[float] = mapped_column(Float)
    payment_date: Mapped[date] = mapped_column(Date)
    reported_physical_progress_pct: Mapped[float] = mapped_column(Float)

    work: Mapped[Work] = relationship(back_populates="payments")


class ProgressReport(Base):
    __tablename__ = "progress_reports"

    report_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_id: Mapped[str] = mapped_column(ForeignKey("works.work_id"), index=True)
    report_date: Mapped[date] = mapped_column(Date, index=True)
    physical_progress_pct: Mapped[float] = mapped_column(Float)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)

    work: Mapped[Work] = relationship(back_populates="progress_reports")


class CompletionPhoto(Base):
    """A site photograph and its metadata.

    ``photo_lat``, ``photo_lon`` and ``capture_timestamp`` are extracted from
    EXIF **server-side** after the file lands in storage. They are never taken
    from the client: the party uploading the photograph is the party the geotag
    check is meant to verify, so client-supplied metadata would make the control
    meaningless.
    """

    __tablename__ = "completion_photos"

    photo_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_id: Mapped[str] = mapped_column(ForeignKey("works.work_id"), index=True)
    upload_date: Mapped[date] = mapped_column(Date)
    capture_timestamp: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    photo_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    photo_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    stage: Mapped[PhotoStage] = mapped_column(enum_col(PhotoStage))

    # Perceptual/content hash. Identical hashes across different works is the
    # signal for PHOTO_REUSED_ACROSS_WORKS.
    image_hash: Mapped[str] = mapped_column(String(64), index=True)
    storage_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

    work: Mapped[Work] = relationship(back_populates="photos")


class AssetHandover(Base):
    """Transfer of a completed asset to the body that will operate it.

    CAG found the handover itself frequently goes unrecorded, leaving an asset
    with no owner on paper. This table is what the Stage 3 module checks against.
    """

    __tablename__ = "asset_handovers"

    handover_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_id: Mapped[str] = mapped_column(ForeignKey("works.work_id"), index=True, unique=True)
    user_agency_id: Mapped[str] = mapped_column(
        ForeignKey("user_agencies.user_agency_id"), index=True
    )
    handover_initiated_date: Mapped[date] = mapped_column(Date)
    handover_acknowledged_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    uc_submitted_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    register_entry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(24), index=True)

    work: Mapped[Work] = relationship()
    user_agency: Mapped[UserAgency] = relationship()


class LifecycleCheckin(Base):
    """A periodic confirmation from the user agency that the asset is still in use."""

    __tablename__ = "lifecycle_checkins"

    checkin_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_id: Mapped[str] = mapped_column(ForeignKey("works.work_id"), index=True)
    checkin_date: Mapped[date] = mapped_column(Date)
    photo_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)
    still_in_use: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    work: Mapped[Work] = relationship()


class MaintenanceRecommendation(Base):
    """A maintenance need raised by the user agency operating the asset.

    This is not a funding request. MPLADS cannot fund maintenance, so the record
    exists to put the need in front of the department that owns the relevant
    budget, and to make the asset's condition visible over its life.
    """

    __tablename__ = "maintenance_recommendations"

    recommendation_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_id: Mapped[str] = mapped_column(ForeignKey("works.work_id"), index=True)
    user_agency_id: Mapped[str] = mapped_column(
        ForeignKey("user_agencies.user_agency_id"), index=True
    )
    raised_date: Mapped[date] = mapped_column(Date)
    description: Mapped[str] = mapped_column(Text)
    photo_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="OPEN", index=True)
    da_response: Mapped[str | None] = mapped_column(Text, nullable=True)

    work: Mapped[Work] = relationship()
    user_agency: Mapped[UserAgency] = relationship()


class CitizenSubmission(Base):
    """Something a member of the public has written in about.

    **Deliberately not a Work.** Under MPLADS only a Member of Parliament may
    recommend a work; a citizen may suggest one. Writing public input straight
    into ``works`` would let an unauthenticated submission enter the screening
    pipeline and appear alongside sanctioned records, which is both wrong on the
    scheme's own terms and an obvious hole. A submission is routed to the Member
    and the District Authority as correspondence, and stops there.

    Nothing here is screened by the engine and no submission ever changes a
    work's state.
    """

    __tablename__ = "citizen_submissions"

    submission_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    submission_type: Mapped[str] = mapped_column(String(24), index=True)

    district_id: Mapped[str] = mapped_column(ForeignKey("districts.district_id"), index=True)
    block: Mapped[str | None] = mapped_column(String(80), nullable=True)

    #: Set only on a concern about an existing work; a suggestion has no work yet.
    related_work_id: Mapped[str | None] = mapped_column(
        ForeignKey("works.work_id"), nullable=True, index=True
    )
    suggested_work_type: Mapped[str | None] = mapped_column(String(48), nullable=True)

    description: Mapped[str] = mapped_column(Text)
    submitter_name: Mapped[str] = mapped_column(String(120))
    #: Optional by design. A citizen should be able to raise something without
    #: leaving a way to be contacted about it.
    submitter_contact: Mapped[str | None] = mapped_column(String(160), nullable=True)

    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    status: Mapped[str] = mapped_column(String(24), default="RECEIVED", index=True)
    official_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    responded_by: Mapped[str | None] = mapped_column(String(120), nullable=True)

    district: Mapped["District"] = relationship()  # noqa: F821
