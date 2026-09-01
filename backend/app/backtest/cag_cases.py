"""CAG backtest — replay documented irregularity patterns through the engine.

Each case reconstructs a pattern the Comptroller and Auditor General documented,
as synthetic records, and runs them through the same engine that screens live
proposals. The claim being made is narrow and checkable: *the method identifies
the classes of irregularity auditors have historically found.*

It is **not** a measurement of real-world accuracy, and nothing here should be
presented as one. The disclaimer on the screen is not decoration.

Cases are built in a scratch in-memory database rather than the working one, so
a backtest run cannot pollute the corpus a reviewer is looking at, and so the
result is identical every time regardless of what else is in the system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.db import Base
from app.engine import runner
from app.engine.context import REFERENCE_DATE, build_context
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
    Work,
)
from app.models.enums import (
    AgencyType,
    House,
    PhotoStage,
    Terrain,
    WorkStatus,
)
from app.engine.engine_config import _file_defaults


@dataclass
class CaseResult:
    case_id: str
    finding: str
    source: str
    pattern: str
    expected_flags: list[str]
    triggered_flags: list[str] = field(default_factory=list)
    unexpected_flags: list[str] = field(default_factory=list)
    works_replayed: int = 0
    works_detected: int = 0

    @property
    def detection_rate(self) -> float:
        return self.works_detected / self.works_replayed if self.works_replayed else 0.0


@dataclass
class CaseSpec:
    case_id: str
    finding: str
    source: str
    pattern: str
    expected_flags: list[str]
    count: int


# Figures are as published. Where a case reconstructs a pattern rather than a
# specific audit paragraph, the pattern line says so.
CASES: list[CaseSpec] = [
    CaseSpec(
        case_id="CAG-01",
        finding="Rs 53.74 crore spent on works inadmissible under the Scheme",
        source="CAG Report No. 31 of 2010, Performance Audit of MPLADS",
        pattern="Works whose type falls outside the MPLADS permissible list.",
        expected_flags=["WORK_TYPE_NOT_PERMISSIBLE"],
        count=20,
    ),
    CaseSpec(
        case_id="CAG-02",
        finding="775 sanctioned works worth Rs 10.18 crore never taken up by agencies",
        source="CAG Report No. 31 of 2010, Performance Audit of MPLADS",
        pattern="Sanctioned, funds fully released, no progress reports and no photographs.",
        expected_flags=["GHOST_WORK", "FULLY_PAID_INCOMPLETE", "NO_COMPLETION_EVIDENCE"],
        count=20,
    ),
    CaseSpec(
        case_id="CAG-03",
        finding="568 works costing Rs 7.30 crore delayed in completion",
        source="CAG Report No. 31 of 2010, Performance Audit of MPLADS",
        pattern="Sanctioned more than twelve months prior, progress still under 100%.",
        expected_flags=["COMPLETION_OVERDUE_12M"],
        count=20,
    ),
    CaseSpec(
        case_id="CAG-04",
        finding="558 works in one state executed without a Member recommendation",
        source="CAG Report No. 31 of 2010, Performance Audit of MPLADS",
        pattern="A sanction date recorded against no recommendation.",
        expected_flags=["MISSING_RECOMMENDATION"],
        count=20,
    ),
    CaseSpec(
        case_id="CAG-05",
        finding="Inflated cost estimation without detailed survey",
        source="Pattern documented across CAG PWD performance audits",
        pattern="Estimates set far above the Schedule of Rates for the work type.",
        expected_flags=["COST_ABOVE_SOR", "COST_PEER_OUTLIER"],
        count=20,
    ),
]

# The permissible-list violations CAG-01 reconstructs.
IMPERMISSIBLE = [
    "MEMORIAL_STATUE",
    "OFFICE_RENOVATION",
    "PLACE_OF_WORSHIP_REPAIR",
    "BOUNDARY_WALL_PRIVATE_TRUST",
]

BENCHMARK = 1_000_000.0


def _scratch_session() -> Session:
    """An isolated database, so a backtest cannot touch the working corpus."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def _seed_reference(db: Session) -> None:
    db.add(
        District(
            district_id="BT-CASE",
            name="Backtest",
            state="Backtest State",
            terrain_category=Terrain.PLAIN,
            centroid_lat=22.0,
            centroid_lon=78.0,
        )
    )
    # Several members rather than one. With a single member the 120 works this
    # module builds breach the annual entitlement between them, and every case
    # picks up an ENTITLEMENT_EXCEEDED that has nothing to do with the pattern
    # it is testing.
    for n in range(8):
        db.add(
            MP(
                mp_id=f"BT-MP-{n}",
                name=f"Backtest Member {n + 1}",
                house=House.LOK_SABHA,
                constituency="Backtest",
                state="Backtest State",
                tenure_start=date(2024, 6, 1),
                tenure_end=date(2029, 5, 31),
                annual_entitlement=50_000_000,
            )
        )
    db.add(
        Agency(
            agency_id="BT-AG",
            name="Backtest PWD",
            agency_type=AgencyType.PWD,
            district_id="BT-CASE",
            registered_date=date(2019, 1, 1),
        )
    )
    for year in (2023, 2024, 2025, 2026):
        for terrain in Terrain:
            db.add(
                SORBenchmark(
                    state="Backtest State",
                    work_type="ROAD_CC",
                    unit="per km",
                    unit_rate=BENCHMARK,
                    year=year,
                    terrain_category=terrain,
                    terrain_multiplier=1.0,
                )
            )

    defaults = _file_defaults()
    for scope in ("stage1", "stage2", "stage3", "tiers", "thresholds", "caps"):
        for key, value in (defaults.get(scope) or {}).items():
            db.add(EngineConfig(scope=scope, key=key, value=float(value), updated_by="backtest"))
    db.flush()


#: Distinct place names, so two works in a case are not near-identical to each
#: other. Without this every case also triggered DUPLICATE_CANDIDATE and
#: SPLIT_WORK_PATTERN — correctly, because the fixture really had built a
#: cluster of identical works, which told a reader nothing about the pattern
#: under test.
_PLACES = [
    "Amarpura", "Bhinder", "Chittora", "Dhanora", "Ekalbara", "Fatehgarh",
    "Gopalpura", "Harsora", "Indragarh", "Jaswantgarh", "Kelwara", "Ladpura",
    "Mandana", "Nayagaon", "Ochhri", "Palri", "Ratanpura", "Sanwar",
    "Tejpura", "Umarwas",
]


def _base_work(work_id: str, index: int = 0, **overrides) -> Work:
    place = _PLACES[index % len(_PLACES)]
    defaults = dict(
        work_id=work_id,
        # Spread across members so no single entitlement is breached.
        mp_id=f"BT-MP-{index % 8}",
        district_id="BT-CASE",
        block=place,
        panchayat=place,
        work_type="ROAD_CC",
        description=(
            f"Construction of cement concrete road with side drains at {place} village, "
            f"reach {index + 1}."
        ),
        estimated_cost=BENCHMARK,
        recommended_date=date(2025, 1, 10),
        sanctioned_date=date(2025, 2, 5),
        expected_completion_date=date(2026, 2, 5),
        status=WorkStatus.IN_PROGRESS,
        agency_id="BT-AG",
        # Unique across the entire run, not merely within a case. `index` is a
        # global sequence, so no two works share a point; 0.01 degrees is about
        # 1.1 km, comfortably outside the 500 m duplicate and 300 m split windows.
        latitude=round(21.5 + index * 0.01, 5),
        longitude=round(77.5 + (index % 9) * 0.05, 5),
        # A quarter in SC/ST areas, comfortably over the mandated share, so the
        # quota rule is satisfied and does not fire across every case.
        is_sc_st_area=(index % 4 == 0),
    )
    defaults.update(overrides)
    return Work(**defaults)


#: Where each case starts in the global position sequence, so cases never
#: overlap each other on the map.
_CASE_OFFSET = {"CAG-01": 0, "CAG-02": 40, "CAG-03": 80, "CAG-04": 120, "CAG-05": 160}
_NORMAL_OFFSET = 220


def _build_case(db: Session, spec: CaseSpec) -> list[str]:
    """Construct the records for one case. Returns the work ids it created."""
    ids: list[str] = []
    base = _CASE_OFFSET[spec.case_id]

    for n in range(spec.count):
        i = base + n
        wid = f"{spec.case_id}-{n:03d}"
        ids.append(wid)

        if spec.case_id == "CAG-01":
            # A work type outside the permissible list.
            db.add(
                _base_work(
                    wid,
                    i,
                    work_type=IMPERMISSIBLE[i % len(IMPERMISSIBLE)],
                    status=WorkStatus.RECOMMENDED,
                    sanctioned_date=None,
                    recommended_date=REFERENCE_DATE - timedelta(days=20),
                )
            )

        elif spec.case_id == "CAG-02":
            # Sanctioned, fully paid, marked complete, no evidence of any kind.
            db.add(
                _base_work(
                    wid,
                    i,
                    status=WorkStatus.COMPLETED,
                    sanctioned_date=date(2024, 6, 1),
                    actual_completion_date=date(2025, 5, 1),
                    final_cost=BENCHMARK,
                )
            )
            db.flush()
            db.add(
                Payment(
                    work_id=wid,
                    installment_no=1,
                    amount=BENCHMARK,
                    payment_date=date(2024, 8, 1),
                    reported_physical_progress_pct=100.0,
                )
            )

        elif spec.case_id == "CAG-03":
            # Sanctioned well over twelve months ago, still incomplete.
            sanctioned = REFERENCE_DATE - timedelta(days=520)
            db.add(
                _base_work(
                    wid,
                    i,
                    status=WorkStatus.IN_PROGRESS,
                    recommended_date=sanctioned - timedelta(days=30),
                    sanctioned_date=sanctioned,
                    expected_completion_date=sanctioned + timedelta(days=365),
                )
            )
            db.flush()
            db.add(
                ProgressReport(
                    work_id=wid,
                    report_date=REFERENCE_DATE - timedelta(days=40),
                    physical_progress_pct=55.0,
                    remarks="Work continuing.",
                )
            )
            db.add(
                Payment(
                    work_id=wid,
                    installment_no=1,
                    amount=BENCHMARK * 0.5,
                    payment_date=sanctioned + timedelta(days=60),
                    reported_physical_progress_pct=55.0,
                )
            )

        elif spec.case_id == "CAG-04":
            # A sanction recorded against no recommendation at all.
            db.add(
                _base_work(
                    wid,
                    i,
                    recommended_date=None,
                    sanctioned_date=date(2025, 3, 1),
                    status=WorkStatus.IN_PROGRESS,
                )
            )
            db.flush()
            db.add(
                ProgressReport(
                    work_id=wid,
                    report_date=REFERENCE_DATE - timedelta(days=30),
                    physical_progress_pct=40.0,
                    remarks="Work continuing.",
                )
            )

        elif spec.case_id == "CAG-05":
            # An estimate far above the Schedule of Rates for the work type.
            db.add(
                _base_work(
                    wid,
                    i,
                    estimated_cost=BENCHMARK * (1.6 + (i % 5) * 0.12),
                    status=WorkStatus.RECOMMENDED,
                    sanctioned_date=None,
                    recommended_date=REFERENCE_DATE - timedelta(days=15),
                )
            )

    db.flush()
    return ids


def run_backtest() -> dict:
    """Build every case, score it, and report what fired.

    Returns a plain dictionary so the API layer does no interpretation of its own.
    """
    with _scratch_session() as db:
        _seed_reference(db)

        case_ids: dict[str, list[str]] = {}
        for spec in CASES:
            case_ids[spec.case_id] = _build_case(db, spec)
        db.commit()

        # CAG-05 needs a peer distribution to compare against, so add a body of
        # ordinary works priced at benchmark. Without them the modified z-score
        # has no population and the peer check cannot fire — which is correct
        # behaviour, but would understate the case.
        for i in range(60):
            db.add(
                _base_work(
                    f"BT-NORMAL-{i:03d}",
                    _NORMAL_OFFSET + i,
                    estimated_cost=BENCHMARK * (0.94 + (i % 11) * 0.012),
                    status=WorkStatus.RECOMMENDED,
                    sanctioned_date=None,
                    recommended_date=REFERENCE_DATE - timedelta(days=25),
                )
            )
        db.commit()

        ctx = build_context(db)
        works = db.scalars(select(Work)).all()
        model = None
        for work in works:
            runner.assess_work(db, work, ctx, model)
        db.commit()

        from app.models.risk import RiskFlag

        flags_by_work: dict[str, set[str]] = {}
        for work_id, code in db.execute(select(RiskFlag.work_id, RiskFlag.flag_code)):
            flags_by_work.setdefault(work_id, set()).add(code)

        results: list[CaseResult] = []
        for spec in CASES:
            ids = case_ids[spec.case_id]
            expected = set(spec.expected_flags)
            triggered: set[str] = set()
            detected = 0
            for wid in ids:
                fired = flags_by_work.get(wid, set())
                triggered |= fired
                if fired & expected:
                    detected += 1
            results.append(
                CaseResult(
                    case_id=spec.case_id,
                    finding=spec.finding,
                    source=spec.source,
                    pattern=spec.pattern,
                    expected_flags=sorted(expected),
                    triggered_flags=sorted(triggered & expected),
                    unexpected_flags=sorted(triggered - expected),
                    works_replayed=len(ids),
                    works_detected=detected,
                )
            )

        return {
            "computed_at": datetime.utcnow().isoformat(timespec="seconds"),
            "engine_version": ctx.config.engine_version,
            "cases": [
                {
                    "case_id": r.case_id,
                    "finding": r.finding,
                    "source": r.source,
                    "pattern": r.pattern,
                    "expected_flags": r.expected_flags,
                    "triggered_flags": r.triggered_flags,
                    "unexpected_flags": r.unexpected_flags,
                    "works_replayed": r.works_replayed,
                    "works_detected": r.works_detected,
                    "detection_rate": round(r.detection_rate, 4),
                }
                for r in results
            ],
            "totals": {
                "works_replayed": sum(r.works_replayed for r in results),
                "works_detected": sum(r.works_detected for r in results),
            },
            "disclaimer": (
                "These cases reproduce irregularity patterns documented in CAG performance "
                "audits, using synthetic records. This demonstrates that the detection method "
                "identifies the classes of irregularity auditors have historically found. It is "
                "not a measurement of real-world detection accuracy, which would require "
                "validation against live MPLADS data."
            ),
        }


def list_cases() -> list[dict]:
    return [
        {
            "case_id": c.case_id,
            "finding": c.finding,
            "source": c.source,
            "pattern": c.pattern,
            "expected_flags": c.expected_flags,
            "works_constructed": c.count,
        }
        for c in CASES
    ]
