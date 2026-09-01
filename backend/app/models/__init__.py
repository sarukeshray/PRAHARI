"""Importing this package registers every table on ``Base.metadata``.

Alembic's env.py imports it for autogenerate, so a new model file must be
re-exported here or its table will silently never be created.
"""

from app.models.enums import (  # noqa: F401
    AgencyType,
    FlagStatus,
    HandoverStatus,
    House,
    MaintenanceStatus,
    ModuleCode,
    PhotoStage,
    PlantedAnomaly,
    ReviewAction,
    Role,
    SeverityTier,
    Stage,
    Terrain,
    UserAgencyType,
    WorkStatus,
)
from app.models.reference import (  # noqa: F401
    MP,
    Agency,
    CostIndex,
    District,
    SORBenchmark,
    User,
    UserAgency,
)
from app.models.risk import (  # noqa: F401
    AgencyResponse,
    EngineConfig,
    FlagReview,
    ModuleContribution,
    RiskAssessment,
    RiskFlag,
)
from app.models.works import (  # noqa: F401
    AssetHandover,
    CompletionPhoto,
    LifecycleCheckin,
    MaintenanceRecommendation,
    Payment,
    ProgressReport,
    Work,
)

__all__ = [
    "MP", "Agency", "AgencyResponse", "AssetHandover", "CompletionPhoto", "CostIndex",
    "District", "EngineConfig", "FlagReview", "LifecycleCheckin",
    "MaintenanceRecommendation", "ModuleContribution", "Payment", "ProgressReport",
    "RiskAssessment", "RiskFlag", "SORBenchmark", "User", "UserAgency", "Work",
]
