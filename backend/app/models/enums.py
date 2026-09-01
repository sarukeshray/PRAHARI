"""Enumerations shared across the schema.

All enums are stored as VARCHAR with a CHECK constraint rather than a native
database ENUM type, so the schema is identical on SQLite and PostgreSQL and a
value can be added without a type migration.
"""

from enum import StrEnum


class House(StrEnum):
    LOK_SABHA = "LOK_SABHA"
    RAJYA_SABHA = "RAJYA_SABHA"
    NOMINATED = "NOMINATED"


class Terrain(StrEnum):
    PLAIN = "PLAIN"
    HILLY = "HILLY"
    REMOTE = "REMOTE"
    COASTAL = "COASTAL"
    URBAN = "URBAN"


class AgencyType(StrEnum):
    PWD = "PWD"
    PRI = "PRI"
    MUNICIPAL = "MUNICIPAL"
    LINE_DEPARTMENT = "LINE_DEPARTMENT"
    OTHER = "OTHER"


class UserAgencyType(StrEnum):
    """The body an asset is handed over to and which then owns its upkeep."""

    SCHOOL = "SCHOOL"
    PANCHAYAT = "PANCHAYAT"
    HEALTH_CENTRE = "HEALTH_CENTRE"
    MUNICIPAL_BODY = "MUNICIPAL_BODY"
    LINE_DEPARTMENT = "LINE_DEPARTMENT"
    OTHER = "OTHER"


class WorkStatus(StrEnum):
    RECOMMENDED = "RECOMMENDED"
    SANCTIONED = "SANCTIONED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"


class PhotoStage(StrEnum):
    START = "START"
    MID = "MID"
    COMPLETE = "COMPLETE"


class Stage(StrEnum):
    STAGE_1 = "STAGE_1"
    STAGE_2 = "STAGE_2"
    STAGE_3 = "STAGE_3"


class SeverityTier(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ModuleCode(StrEnum):
    # Stage 1 — pre-sanction
    COST = "COST"
    DUPLICATE = "DUPLICATE"
    AGENCY = "AGENCY"
    COMPLIANCE = "COMPLIANCE"
    STATISTICAL = "STATISTICAL"
    # Stage 2 — post-sanction
    DISBURSEMENT = "DISBURSEMENT"
    GEOTAG = "GEOTAG"
    VARIANCE = "VARIANCE"
    TIMELINE = "TIMELINE"
    # Stage 3 — handover and lifecycle
    HANDOVER = "HANDOVER"


class FlagStatus(StrEnum):
    OPEN = "OPEN"
    UNDER_INVESTIGATION = "UNDER_INVESTIGATION"
    OVERRIDDEN = "OVERRIDDEN"
    CLEARED = "CLEARED"


class ReviewAction(StrEnum):
    INVESTIGATE = "INVESTIGATE"
    OVERRIDE = "OVERRIDE"
    CLEAR = "CLEAR"


class HandoverStatus(StrEnum):
    PENDING = "PENDING"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    OVERDUE = "OVERDUE"


class MaintenanceStatus(StrEnum):
    OPEN = "OPEN"
    ACKNOWLEDGED_BY_DA = "ACKNOWLEDGED_BY_DA"
    CLOSED = "CLOSED"


class Role(StrEnum):
    """The seven access roles. Scoping rules live on the User model."""

    DISTRICT_AUTHORITY = "DISTRICT_AUTHORITY"
    MP = "MP"
    MINISTRY = "MINISTRY"
    STATE_NODAL = "STATE_NODAL"
    IMPLEMENTING_AGENCY = "IMPLEMENTING_AGENCY"
    USER_AGENCY = "USER_AGENCY"
    PUBLIC = "PUBLIC"


class PlantedAnomaly(StrEnum):
    """Evaluation labels only.

    Written by the synthetic generator and read by the backtest and sensitivity
    reports. The engine never reads this column, and it is never exposed on any
    reviewer-facing screen.
    """

    COST_INFLATION = "COST_INFLATION"
    DUPLICATE_WORK = "DUPLICATE_WORK"
    SALAMI_SLICING = "SALAMI_SLICING"
    PAYMENT_AHEAD = "PAYMENT_AHEAD"
    GEOTAG_MISMATCH = "GEOTAG_MISMATCH"
    PHOTO_REUSE = "PHOTO_REUSE"
    TIMELINE_BREACH = "TIMELINE_BREACH"
    COST_OVERRUN = "COST_OVERRUN"
    GHOST_WORK = "GHOST_WORK"
    ENTITLEMENT_BREACH = "ENTITLEMENT_BREACH"
    QUOTA_SHORTFALL = "QUOTA_SHORTFALL"
    HANDOVER_GAP = "HANDOVER_GAP"
