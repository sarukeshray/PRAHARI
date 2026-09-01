"""Fixtures: a small in-memory corpus with known values.

Deliberately hand-built rather than generated. Every number here is one a test
can assert against by hand, so a failure points at the module rather than at the
generator.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db import Base
from app.engine.context import EngineContext, build_context
from app.models import (
    MP,
    Agency,
    AssetHandover,
    CompletionPhoto,
    District,
    EngineConfig,
    Payment,
    ProgressReport,
    SORBenchmark,
    UserAgency,
    Work,
)
from app.models.enums import (
    AgencyType,
    HandoverStatus,
    House,
    PhotoStage,
    Terrain,
    UserAgencyType,
    WorkStatus,
)

TODAY = date(2026, 8, 31)

# One benchmark everything is measured against, so deviations are easy to read.
# ROAD_CC in PLAIN terrain, 2025 rates.
BENCHMARK = 1_000_000.0


@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, expire_on_commit=False)
    with maker() as session:
        _seed(session)
        session.commit()
        yield session


def _seed(db: Session) -> None:
    db.add(
        District(
            district_id="TT-AAA",
            name="Testville",
            state="Teststate",
            terrain_category=Terrain.PLAIN,
            centroid_lat=20.0,
            centroid_lon=78.0,
        )
    )
    db.add(
        MP(
            mp_id="MP-001",
            name="Dr. T. Example",
            house=House.LOK_SABHA,
            constituency="Testville",
            state="Teststate",
            tenure_start=date(2024, 6, 1),
            tenure_end=date(2029, 5, 31),
            annual_entitlement=50_000_000,
        )
    )
    db.add(
        Agency(
            agency_id="AG-001",
            name="PWD Division Testville",
            agency_type=AgencyType.PWD,
            district_id="TT-AAA",
            registered_date=date(2019, 1, 1),
        )
    )
    db.add(
        UserAgency(
            user_agency_id="UA-001",
            name="Gram Panchayat Testville",
            user_agency_type=UserAgencyType.PANCHAYAT,
            district_id="TT-AAA",
        )
    )

    # Rates for every year, escalating. A work is compared against its own year,
    # which is what the inflation test exercises.
    for year, rate in [(2023, 880_000.0), (2024, 935_000.0), (2025, BENCHMARK), (2026, 1_062_000.0)]:
        for terrain in Terrain:
            db.add(
                SORBenchmark(
                    state="Teststate",
                    work_type="ROAD_CC",
                    unit="per km",
                    unit_rate=rate,
                    year=year,
                    terrain_category=terrain,
                    terrain_multiplier=1.0,
                )
            )
    db.flush()


def make_work(
    db: Session,
    work_id: str,
    *,
    cost: float = BENCHMARK,
    status: WorkStatus = WorkStatus.RECOMMENDED,
    recommended: date | None = None,
    sanctioned: date | None = None,
    completed: date | None = None,
    final_cost: float | None = None,
    description: str = "Construction of cement concrete road at Testville village.",
    lat: float = 20.0,
    lon: float = 78.0,
    agency_id: str | None = "AG-001",
    work_type: str = "ROAD_CC",
    sc_st: bool = False,
) -> Work:
    work = Work(
        work_id=work_id,
        mp_id="MP-001",
        district_id="TT-AAA",
        block="Central",
        panchayat="Testville",
        work_type=work_type,
        description=description,
        estimated_cost=cost,
        final_cost=final_cost,
        recommended_date=recommended if recommended is not None else date(2025, 6, 1),
        sanctioned_date=sanctioned,
        expected_completion_date=(sanctioned + timedelta(days=365)) if sanctioned else None,
        actual_completion_date=completed,
        status=status,
        agency_id=agency_id,
        latitude=lat,
        longitude=lon,
        is_sc_st_area=sc_st,
    )
    db.add(work)
    db.flush()
    return work


def add_payment(db: Session, work: Work, pct: float, progress: float = 0.0) -> None:
    db.add(
        Payment(
            work_id=work.work_id,
            installment_no=1,
            amount=work.estimated_cost * pct / 100,
            payment_date=(work.sanctioned_date or TODAY) + timedelta(days=30),
            reported_physical_progress_pct=progress,
        )
    )
    db.flush()


def add_progress(db: Session, work: Work, pct: float, when: date | None = None) -> None:
    db.add(
        ProgressReport(
            work_id=work.work_id,
            report_date=when or TODAY - timedelta(days=10),
            physical_progress_pct=pct,
            remarks="Test report.",
        )
    )
    db.flush()


def add_photo(
    db: Session,
    work: Work,
    *,
    lat: float | None = None,
    lon: float | None = None,
    captured: date | None = None,
    image_hash: str = "hash-default",
    stage: PhotoStage = PhotoStage.COMPLETE,
) -> None:
    db.add(
        CompletionPhoto(
            work_id=work.work_id,
            upload_date=TODAY,
            capture_timestamp=datetime.combine(captured or TODAY, datetime.min.time()),
            photo_lat=lat if lat is not None else work.latitude,
            photo_lon=lon if lon is not None else work.longitude,
            stage=stage,
            image_hash=image_hash,
        )
    )
    db.flush()


def add_handover(
    db: Session,
    work: Work,
    *,
    initiated: date,
    acknowledged: date | None = None,
    uc: date | None = None,
    register: date | None = None,
) -> None:
    db.add(
        AssetHandover(
            work_id=work.work_id,
            user_agency_id="UA-001",
            handover_initiated_date=initiated,
            handover_acknowledged_date=acknowledged,
            uc_submitted_date=uc,
            register_entry_date=register,
            status=HandoverStatus.ACKNOWLEDGED if acknowledged else HandoverStatus.PENDING,
        )
    )
    db.flush()


def ctx_for(db: Session) -> EngineContext:
    return build_context(db, reference_date=TODAY)
