"""Request and response shapes.

Two things these deliberately do NOT expose:

* ``works.planted_anomaly`` — the evaluation answer key. It never leaves the
  database except through the backtest endpoint, which reports aggregate
  sensitivity rather than per-work labels.
* Raw composite scores as a headline. The score is present on the assessment for
  traceability, but the tier and the explanation lead everywhere a person reads.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import (
    FlagStatus,
    ModuleCode,
    ReviewAction,
    Role,
    SeverityTier,
    Stage,
    WorkStatus,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Findings and assessments
# ---------------------------------------------------------------------------


class ReviewOut(ORMModel):
    review_id: int
    reviewer_role: Role
    reviewer_name: str
    action: ReviewAction
    justification: str | None
    decided_at: datetime


class FlagOut(ORMModel):
    flag_id: int
    work_id: str
    module: ModuleCode
    flag_code: str
    signal_value: float
    threshold_value: float
    severity_tier: SeverityTier
    explanation: str
    status: FlagStatus
    created_at: datetime
    assigned_to_user_id: str | None = None
    reviews: list[ReviewOut] = Field(default_factory=list)


class ContributionOut(ORMModel):
    module: ModuleCode
    score: float
    weight: float

    @property
    def contribution(self) -> float:
        return self.score * self.weight


class AssessmentOut(ORMModel):
    assessment_id: int
    stage: Stage
    composite_score: float
    severity_tier: SeverityTier
    engine_version: str
    computed_at: datetime
    contributions: list[ContributionOut] = Field(default_factory=list)
    flags: list[FlagOut] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Works
# ---------------------------------------------------------------------------


class WorkSummary(ORMModel):
    """The row shape for a queue or table."""

    work_id: str
    work_type: str
    description: str
    block: str
    district_id: str
    district_name: str | None = None
    estimated_cost: float
    final_cost: float | None
    status: WorkStatus
    recommended_date: date | None
    sanctioned_date: date | None
    mp_name: str | None = None
    agency_name: str | None = None
    latitude: float
    longitude: float
    is_sc_st_area: bool

    severity_tier: SeverityTier | None = None
    composite_score: float | None = None
    open_flag_count: int = 0
    primary_finding: str | None = None
    primary_finding_title: str | None = None
    days_open: int | None = None


class WorkDetail(WorkSummary):
    panchayat: str | None = None
    state: str | None = None
    terrain_category: str | None = None
    constituency: str | None = None
    house: str | None = None
    agency_type: str | None = None
    expected_completion_date: date | None = None
    actual_completion_date: date | None = None
    disbursed_amount: float = 0.0
    disbursed_pct: float = 0.0
    latest_progress_pct: float = 0.0
    photo_count: int = 0
    report_count: int = 0
    assessments: list[AssessmentOut] = Field(default_factory=list)


class WorkRecommendation(BaseModel):
    """What a Member submits. Screening runs on save."""

    district_id: str
    block: str
    panchayat: str | None = None
    work_type: str
    description: str = Field(min_length=20, max_length=600)
    estimated_cost: float = Field(gt=0)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    is_sc_st_area: bool = False
    agency_id: str | None = None


# ---------------------------------------------------------------------------
# Review workflow
# ---------------------------------------------------------------------------

MIN_JUSTIFICATION = 20


class ReviewRequest(BaseModel):
    action: ReviewAction
    reviewer_name: str | None = None
    justification: str = ""

    @field_validator("justification")
    @classmethod
    def _strip(cls, v: str) -> str:
        return (v or "").strip()

    def validate_for_action(self) -> None:
        """An override must be justified in writing.

        Enforced at the API boundary rather than only in the interface, because
        the interface is not the only way to reach this endpoint. Overriding a
        finding leaves it on the record with a reason attached; that reason is
        the entire accountability mechanism, so an empty one is refused.
        """
        from fastapi import HTTPException, status

        if self.action is ReviewAction.OVERRIDE and len(self.justification) < MIN_JUSTIFICATION:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Overriding a finding requires a written justification of at least "
                    f"{MIN_JUSTIFICATION} characters. It is recorded against the work and "
                    f"is what makes the decision reviewable."
                ),
            )


class ReassignRequest(BaseModel):
    assigned_to_user_id: str
    note: str = ""


# ---------------------------------------------------------------------------
# Stage 3 — lifecycle
# ---------------------------------------------------------------------------


class HandoverOut(ORMModel):
    handover_id: int
    work_id: str
    user_agency_id: str
    user_agency_name: str | None = None
    handover_initiated_date: date
    handover_acknowledged_date: date | None
    uc_submitted_date: date | None
    register_entry_date: date | None
    status: str


class CheckinOut(ORMModel):
    checkin_id: int
    work_id: str
    checkin_date: date
    photo_reference: str | None
    still_in_use: bool
    notes: str | None


class CheckinRequest(BaseModel):
    still_in_use: bool = True
    notes: str = Field(default="", max_length=600)
    photo_reference: str | None = None


class MaintenanceOut(ORMModel):
    recommendation_id: int
    work_id: str
    user_agency_id: str
    raised_date: date
    description: str
    photo_reference: str | None
    status: str
    da_response: str | None


class MaintenanceRequest(BaseModel):
    """A maintenance need raised by the body operating the asset.

    Explicitly not a funding request: MPLADS cannot fund maintenance. The record
    puts the need in front of the department whose budget can.
    """

    description: str = Field(min_length=15, max_length=800)
    photo_reference: str | None = None


class AssetSummary(ORMModel):
    work_id: str
    work_type: str
    description: str
    block: str
    completed_on: date | None
    handover: HandoverOut | None = None
    checkins: list[CheckinOut] = Field(default_factory=list)
    maintenance: list[MaintenanceOut] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Dashboards
# ---------------------------------------------------------------------------


class TierCounts(BaseModel):
    CRITICAL: int = 0
    HIGH: int = 0
    MEDIUM: int = 0
    LOW: int = 0


class ModuleCount(BaseModel):
    module: ModuleCode
    count: int


class TrendPoint(BaseModel):
    period: str
    count: int


class DistrictSummary(BaseModel):
    district_id: str
    district_name: str
    state: str
    works_total: int
    works_screened: int
    open_findings: int
    tier_counts: TierCounts
    by_module: list[ModuleCount]
    trend: list[TrendPoint]
    handover_overdue: int


class AgencyPerformance(BaseModel):
    agency_id: str
    name: str
    terrain_category: str
    percentile: float
    peer_count: int
    peer_group_label: str
    completed_works: int
    total_works: int
    completion_rate: float
    mean_delay_days: float
    mean_overrun_pct: float
    #: Every agency in the same peer group, so the percentile can be seen in context.
    peer_percentiles: list[float] = Field(default_factory=list)
    flagged: bool = False
    note: str = ""


class PublicAggregate(BaseModel):
    """The only shape the public endpoint returns.

    No work identifiers, no agency names, no member names, no findings. What a
    citizen may see is how much was spent and how much was finished.
    """

    state: str
    works_total: int
    works_completed: int
    completion_rate_pct: float
    sanctioned_amount: float
    disbursed_amount: float
    utilisation_pct: float
