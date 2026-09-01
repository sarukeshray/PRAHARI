"""Assessments, findings, and the human decisions recorded against them."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import (
    FlagStatus,
    ModuleCode,
    ReviewAction,
    Role,
    SeverityTier,
    Stage,
)
from app.models.reference import enum_col
from app.models.works import Work


class RiskAssessment(Base):
    """One engine run over one work at one stage."""

    __tablename__ = "risk_assessments"

    assessment_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_id: Mapped[str] = mapped_column(ForeignKey("works.work_id"), index=True)
    stage: Mapped[Stage] = mapped_column(enum_col(Stage), index=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    composite_score: Mapped[float] = mapped_column(Float)
    severity_tier: Mapped[SeverityTier] = mapped_column(enum_col(SeverityTier), index=True)

    # Stamped on every assessment so a score stays traceable after weights change.
    engine_version: Mapped[str] = mapped_column(String(24))

    work: Mapped[Work] = relationship()
    flags: Mapped[list["RiskFlag"]] = relationship(
        back_populates="assessment", cascade="all, delete"
    )
    contributions: Mapped[list["ModuleContribution"]] = relationship(
        back_populates="assessment", cascade="all, delete"
    )


class ModuleContribution(Base):
    """One module's score and weight within an assessment.

    Persisted rather than recomputed so the breakdown a reviewer saw at decision
    time can be reproduced exactly, even after the weights are retuned.
    """

    __tablename__ = "module_contributions"
    __table_args__ = (
        UniqueConstraint("assessment_id", "module", name="uq_contribution_assessment_module"),
    )

    contribution_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("risk_assessments.assessment_id"), index=True
    )
    module: Mapped[ModuleCode] = mapped_column(enum_col(ModuleCode))
    score: Mapped[float] = mapped_column(Float)
    weight: Mapped[float] = mapped_column(Float)

    assessment: Mapped[RiskAssessment] = relationship(back_populates="contributions")


class RiskFlag(Base):
    """A single finding requiring human review.

    ``signal_value`` and ``threshold_value`` are stored alongside the rendered
    explanation so the claim in the sentence can always be checked against the
    numbers that produced it.
    """

    __tablename__ = "risk_flags"

    flag_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("risk_assessments.assessment_id"), index=True
    )
    work_id: Mapped[str] = mapped_column(ForeignKey("works.work_id"), index=True)
    module: Mapped[ModuleCode] = mapped_column(enum_col(ModuleCode), index=True)
    flag_code: Mapped[str] = mapped_column(String(48), index=True)

    signal_value: Mapped[float] = mapped_column(Float)
    threshold_value: Mapped[float] = mapped_column(Float)
    severity_tier: Mapped[SeverityTier] = mapped_column(enum_col(SeverityTier), index=True)
    explanation: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    status: Mapped[FlagStatus] = mapped_column(
        enum_col(FlagStatus), default=FlagStatus.OPEN, index=True
    )

    # Set by the State Nodal reassign action; null means unassigned.
    assigned_to_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.user_id"), nullable=True, index=True
    )

    assessment: Mapped[RiskAssessment] = relationship(back_populates="flags")
    work: Mapped[Work] = relationship()
    reviews: Mapped[list["FlagReview"]] = relationship(
        back_populates="flag", cascade="all, delete", order_by="FlagReview.decided_at.desc()"
    )


class FlagReview(Base):
    """A human decision on a finding.

    The only three transitions a finding can undergo, and all three are recorded
    with who made them. An OVERRIDE without a justification is rejected at the
    API boundary, not merely discouraged in the interface.
    """

    __tablename__ = "flag_reviews"

    review_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    flag_id: Mapped[int] = mapped_column(ForeignKey("risk_flags.flag_id"), index=True)
    reviewer_role: Mapped[Role] = mapped_column(enum_col(Role))
    reviewer_name: Mapped[str] = mapped_column(String(120))
    action: Mapped[ReviewAction] = mapped_column(enum_col(ReviewAction))
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    flag: Mapped[RiskFlag] = relationship(back_populates="reviews")


class AgencyResponse(Base):
    """An implementing agency's reply to a finding on one of its own works.

    A response never clears a finding. It routes back to the District Authority
    as new evidence for a person to weigh, which keeps the no-automated-
    consequence rule intact even when the responder is the party being asked about.
    """

    __tablename__ = "agency_responses"

    response_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    flag_id: Mapped[int] = mapped_column(ForeignKey("risk_flags.flag_id"), index=True)
    agency_id: Mapped[str] = mapped_column(ForeignKey("agencies.agency_id"), index=True)
    submitted_date: Mapped[date] = mapped_column(Date)
    note: Mapped[str] = mapped_column(Text)
    evidence_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)

    flag: Mapped[RiskFlag] = relationship()


class EngineConfig(Base):
    """Scoring weights and thresholds, editable by the Ministry role.

    Seeded from ``config/weights.yaml``; the database wins once a row exists, so
    the file stays as the documented default and a change through the interface
    takes effect on the next scoring run.
    """

    __tablename__ = "engine_config"
    __table_args__ = (UniqueConstraint("scope", "key", name="uq_engine_config_scope_key"),)

    config_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scope: Mapped[str] = mapped_column(String(32), index=True)  # "stage1" | "stage2" | "stage3" | "threshold"
    key: Mapped[str] = mapped_column(String(48))
    value: Mapped[float] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
