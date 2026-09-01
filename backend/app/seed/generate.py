"""Synthetic MPLADS dataset generator.

    python -m app.seed.generate --works 4000 --seed 42 --reset

Produces an eSAKSHI-shaped dataset with a labelled subset of planted anomalies,
so detection can be measured against a known answer key. Deterministic under
``--seed`` — the same seed produces byte-identical output, which is what makes
the demo and the sensitivity numbers reproducible.

Structure: build a clean population first, then apply anomaly transformations in
two passes. Per-work anomalies (an inflated cost, a mismatched geotag) change one
record. Structural anomalies (a duplicate pair, a split cluster, an entitlement
breach) need several records arranged in relation to each other, so they run
afterwards over works already placed on the map and the calendar.

Nothing here is a real record. Place names are real; every person, agency, work
and rupee figure is invented.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import random
from collections import defaultdict
from datetime import date, datetime, timedelta

import yaml
from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.config.settings import BACKEND_ROOT, settings
from app.db import SessionLocal
from app.models import (
    MP,
    Agency,
    AssetHandover,
    CompletionPhoto,
    CostIndex,
    District,
    EngineConfig,
    LifecycleCheckin,
    MaintenanceRecommendation,
    Payment,
    ProgressReport,
    SORBenchmark,
    User,
    UserAgency,
    Work,
)
from app.models.enums import (
    HandoverStatus,
    House,
    PhotoStage,
    PlantedAnomaly,
    Role,
    Terrain,
    WorkStatus,
)
from app.seed import catalog as cat

# The dataset's "today". Fixed rather than wall-clock so ages, overdue windows
# and isolation-forest features are stable across runs — a report generated in
# March must match one generated in September.
REFERENCE_DATE = date(2026, 8, 31)

ANOMALY_SHARE = 0.12

# Every anomaly type gets at least this many instances regardless of dataset
# size. Recall on five examples is noise; the sensitivity table needs a floor
# it can actually stand on.
MIN_PER_ANOMALY = 30


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def sor_rate(base: float, year: int, terrain: Terrain) -> float:
    """Schedule of Rates for a work type in a given year and terrain."""
    escalated = base * ((1 + cat.SOR_ANNUAL_ESCALATION) ** (year - cat.SOR_BASE_YEAR))
    return round(escalated * cat.TERRAIN_MULTIPLIER[terrain], 2)


def jitter_point(rng: random.Random, lat: float, lon: float, km: float) -> tuple[float, float]:
    """A random point within roughly ``km`` of a centre."""
    r = km * math.sqrt(rng.random()) / 111.0
    theta = rng.uniform(0, 2 * math.pi)
    return round(lat + r * math.cos(theta), 6), round(lon + r * math.sin(theta), 6)


def offset_point(lat: float, lon: float, metres: float, bearing_deg: float) -> tuple[float, float]:
    """A point an exact distance and bearing from another."""
    d = metres / 111_320.0
    b = math.radians(bearing_deg)
    return round(lat + d * math.cos(b), 6), round(lon + d * math.sin(b) / math.cos(math.radians(lat)), 6)


def image_hash(seed: str) -> str:
    return hashlib.sha256(seed.encode()).hexdigest()[:32]


def financial_year_of(d: date) -> int:
    """Indian financial year starting year: April to March."""
    return d.year if d.month >= 4 else d.year - 1


def make_description(rng: random.Random, work_type: str, panchayat: str) -> str:
    detail = rng.choice(cat.DESC_DETAIL.get(work_type, ["public utility work"]))
    location = rng.choice(cat.DESC_LOCATION).format(panchayat=panchayat, ward=rng.randint(1, 18))
    return f"{rng.choice(cat.DESC_ACTION)} {detail} {location} {rng.choice(cat.DESC_SUFFIX)}"


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------


def seed_reference(db: Session, rng: random.Random) -> dict:
    districts: list[District] = []
    for did, name, state, terrain, lat, lon in cat.DISTRICTS:
        districts.append(
            District(
                district_id=did,
                name=name,
                state=state,
                terrain_category=terrain,
                centroid_lat=lat,
                centroid_lon=lon,
            )
        )
    db.add_all(districts)

    # Schedule of Rates: one row per state, work type, year and terrain.
    for state in sorted({d.state for d in districts}):
        for work_type, (unit, base, _) in cat.WORK_TYPES.items():
            for year in cat.SOR_YEARS:
                for terrain in Terrain:
                    db.add(
                        SORBenchmark(
                            state=state,
                            work_type=work_type,
                            unit=unit,
                            unit_rate=sor_rate(base, year, terrain),
                            year=year,
                            terrain_category=terrain,
                            terrain_multiplier=cat.TERRAIN_MULTIPLIER[terrain],
                        )
                    )

    for year, value in cat.COST_INDEX.items():
        db.add(CostIndex(year=year, index_value=value, source="CPWD (illustrative)"))

    # Members: roughly three or four per district's state, Lok Sabha and Rajya Sabha.
    mps: list[MP] = []
    for i in range(40):
        state = cat.DISTRICTS[i % len(cat.DISTRICTS)][2]
        constituency = cat.DISTRICTS[i % len(cat.DISTRICTS)][1]
        house = House.RAJYA_SABHA if i % 5 == 4 else House.LOK_SABHA
        name = f"{rng.choice(cat.MP_HONORIFIC)} {rng.choice(cat.MP_FIRST)} {rng.choice(cat.MP_LAST)}"
        mps.append(
            MP(
                mp_id=f"MP-{i + 1:03d}",
                name=name,
                house=house,
                constituency=state if house == House.RAJYA_SABHA else constituency,
                state=state,
                tenure_start=date(2024, 6, 1),
                tenure_end=date(2029, 5, 31),
                annual_entitlement=50_000_000,
            )
        )
    db.add_all(mps)

    agencies: list[Agency] = []
    for district in districts:
        for tmpl, atype in cat.AGENCY_TEMPLATES:
            agencies.append(
                Agency(
                    agency_id=f"AG-{len(agencies) + 1:04d}",
                    name=tmpl.format(district=district.name),
                    agency_type=atype,
                    district_id=district.district_id,
                    registered_date=date(2018 + rng.randint(0, 4), rng.randint(1, 12), 1),
                )
            )
    db.add_all(agencies)

    user_agencies: list[UserAgency] = []
    for district in districts:
        for block in cat.BLOCKS[district.district_id][:4]:
            tmpl, uatype = cat.USER_AGENCY_TEMPLATES[len(user_agencies) % len(cat.USER_AGENCY_TEMPLATES)]
            user_agencies.append(
                UserAgency(
                    user_agency_id=f"UA-{len(user_agencies) + 1:04d}",
                    name=tmpl.format(block=block),
                    user_agency_type=uatype,
                    district_id=district.district_id,
                    contact_name=rng.choice(cat.OFFICER_NAMES),
                )
            )
    db.add_all(user_agencies)

    db.flush()
    return {"districts": districts, "mps": mps, "agencies": agencies, "user_agencies": user_agencies}


def seed_users(db: Session, ref: dict) -> None:
    """One demo account per role, plus a second District Authority for reassignment.

    Passwords live in Firebase, not here. These rows carry the role and the data
    scope the API derives every query filter from.
    """
    udr = "RJ-UDR"
    agency = next(a for a in ref["agencies"] if a.district_id == udr)
    user_agency = next(u for u in ref["user_agencies"] if u.district_id == udr)
    mp = next(m for m in ref["mps"] if m.constituency == "Udaipur")

    rows = [
        User(
            user_id="u-da-udaipur", email="da.udaipur@prahari.demo", display_name="S. Nair, IAS",
            role=Role.DISTRICT_AUTHORITY, scope_district_id=udr, scope_state="Rajasthan",
        ),
        User(
            user_id="u-da-udaipur-2", email="da2.udaipur@prahari.demo", display_name="R. Deshmukh",
            role=Role.DISTRICT_AUTHORITY, scope_district_id=udr, scope_state="Rajasthan",
        ),
        User(
            user_id="u-mp", email="mp.udaipur@prahari.demo", display_name=mp.name,
            role=Role.MP, scope_mp_id=mp.mp_id, scope_state=mp.state,
        ),
        User(
            user_id="u-ministry", email="diid@prahari.demo", display_name="DIID Monitoring Cell",
            role=Role.MINISTRY,
        ),
        User(
            user_id="u-state-rj", email="sna.rajasthan@prahari.demo", display_name="A. Krishnan",
            role=Role.STATE_NODAL, scope_state="Rajasthan",
        ),
        User(
            user_id="u-agency", email="pwd.udaipur@prahari.demo", display_name=agency.name,
            role=Role.IMPLEMENTING_AGENCY, scope_agency_id=agency.agency_id,
            scope_district_id=udr, scope_state="Rajasthan",
        ),
        User(
            user_id="u-useragency", email="useragency.udaipur@prahari.demo",
            display_name=user_agency.name, role=Role.USER_AGENCY,
            scope_user_agency_id=user_agency.user_agency_id, scope_district_id=udr,
            scope_state="Rajasthan",
        ),
        User(
            user_id="u-public", email="public@prahari.demo", display_name="Public",
            role=Role.PUBLIC,
        ),
    ]
    db.add_all(rows)


def seed_engine_config(db: Session) -> str:
    """Load weights.yaml into engine_config so the Ministry screen can retune it."""
    path = BACKEND_ROOT / "app" / "config" / "weights.yaml"
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))

    for scope in ("stage1", "stage2", "stage3", "tiers", "thresholds", "caps"):
        for key, value in (cfg.get(scope) or {}).items():
            db.add(EngineConfig(scope=scope, key=key, value=float(value), updated_by="seed"))

    return cfg["engine_version"]


# ---------------------------------------------------------------------------
# Clean population
# ---------------------------------------------------------------------------


def build_works(db: Session, rng: random.Random, ref: dict, count: int) -> list[Work]:
    districts: list[District] = ref["districts"]
    mps: list[MP] = ref["mps"]
    agencies_by_district: dict[str, list[Agency]] = defaultdict(list)
    for a in ref["agencies"]:
        agencies_by_district[a.district_id].append(a)

    # Lok Sabha members recommend only within their own constituency; Rajya
    # Sabha members may recommend anywhere in their state.
    ls_by_constituency: dict[str, list[MP]] = defaultdict(list)
    rs_by_state: dict[str, list[MP]] = defaultdict(list)
    for m in mps:
        if m.house == House.LOK_SABHA:
            ls_by_constituency[m.constituency].append(m)
        else:
            rs_by_state[m.state].append(m)

    work_types = list(cat.WORK_TYPES)
    works: list[Work] = []
    mp_year_spend: dict[tuple, float] = defaultdict(float)

    for i in range(count):
        district = districts[i % len(districts)]
        block = rng.choice(cat.BLOCKS[district.district_id])
        panchayat = rng.choice(cat.BLOCKS[district.district_id])
        work_type = rng.choice(work_types)
        eligible = ls_by_constituency.get(district.name, []) + rs_by_state.get(district.state, [])
        if not eligible:
            eligible = mps

        # Spread recommendations across three financial years.
        recommended = REFERENCE_DATE - timedelta(days=rng.randint(20, 1080))
        year = recommended.year

        base = cat.WORK_TYPES[work_type][1]
        benchmark = sor_rate(base, min(year, max(cat.SOR_YEARS)), district.terrain_category)

        # Log-normal around the benchmark: most works land near it, a genuine
        # tail sits above without being planted. sigma keeps ~95% inside ±25%,
        # so the ordinary population does not trip COST_ABOVE_SOR on its own.
        estimated = round(benchmark * rng.lognormvariate(0, 0.11), 2)

        # Give the work to a member who still has room this year. Purely random
        # assignment pushed some member-years past the entitlement by accident,
        # producing 139 compliance findings nobody planted.
        fy_key = financial_year_of(recommended)
        headroom = [
            m
            for m in eligible
            if mp_year_spend[(m.mp_id, fy_key)] + estimated <= m.annual_entitlement * 0.92
        ]
        mp = rng.choice(headroom) if headroom else min(
            eligible, key=lambda m: mp_year_spend[(m.mp_id, fy_key)]
        )
        mp_year_spend[(mp.mp_id, fy_key)] += estimated

        lat, lon = jitter_point(rng, district.centroid_lat, district.centroid_lon, 35)

        work = Work(
            work_id=f"{district.district_id}-{i + 1:05d}",
            mp_id=mp.mp_id,
            district_id=district.district_id,
            block=block,
            panchayat=panchayat,
            work_type=work_type,
            description=make_description(rng, work_type, panchayat),
            estimated_cost=estimated,
            recommended_date=recommended,
            status=WorkStatus.RECOMMENDED,
            latitude=lat,
            longitude=lon,
            is_sc_st_area=rng.random() < 0.24,
            planted_anomaly=None,
        )

        # Advance the work along its lifecycle according to its age.
        # The proposing note normally names an implementing agency, so the
        # agency record is available to pre-sanction screening.
        work.agency_id = rng.choice(agencies_by_district[district.district_id]).agency_id

        awaiting_decision = rng.random() < 0.15
        if awaiting_decision:
            # A pending proposal is usually a recent one. Leaving them spread
            # across three years made 88% of the pending queue overdue against
            # the 45-day guideline, which is not what a functioning district
            # looks like. A quarter are still genuinely stale, which is what
            # SANCTION_DELAY_45D exists to surface.
            stale = rng.random() < 0.25
            span = rng.randint(200, 900) if stale else rng.randint(3, 40)
            recommended = REFERENCE_DATE - timedelta(days=span)
            work.recommended_date = recommended
            if stale:
                # Overdue for a decision - exactly what SANCTION_DELAY_45D
                # looks for, so it belongs in the answer key rather than
                # sitting unlabelled in the clean population.
                work.planted_anomaly = PlantedAnomaly.TIMELINE_BREACH

        age = (REFERENCE_DATE - recommended).days
        if age > 60 and not awaiting_decision:
            work.sanctioned_date = recommended + timedelta(days=rng.randint(12, 44))
            work.expected_completion_date = work.sanctioned_date + timedelta(days=365)
            work.status = WorkStatus.SANCTIONED
            # Only a sanctioned work can progress. One left awaiting a decision
            # stays RECOMMENDED however old it is, which is the point.
            if age > 150:
                work.status = WorkStatus.IN_PROGRESS
            # Works with no planted anomaly should finish inside the guideline;
            # a stale clean work is a finding the answer key does not know about.
            if age > 400:
                work.status = WorkStatus.COMPLETED
                work.actual_completion_date = work.sanctioned_date + timedelta(
                    days=rng.randint(200, 350)
                )
                work.final_cost = round(work.estimated_cost * rng.uniform(0.98, 1.09), 2)

        works.append(work)

    db.add_all(works)
    db.flush()
    return works


def build_downstream(db: Session, rng: random.Random, works: list[Work], ref: dict) -> None:
    """Payments, progress reports, photographs and handovers for works underway."""
    user_agencies_by_district: dict[str, list[UserAgency]] = defaultdict(list)
    for ua in ref["user_agencies"]:
        user_agencies_by_district[ua.district_id].append(ua)

    for w in works:
        if w.sanctioned_date is None:
            continue

        progress = {
            WorkStatus.SANCTIONED: rng.uniform(0, 20),
            WorkStatus.IN_PROGRESS: rng.uniform(25, 85),
            WorkStatus.COMPLETED: 100.0,
        }.get(w.status, 0.0)

        # Progress reports roughly quarterly since sanction.
        span = (REFERENCE_DATE - w.sanctioned_date).days
        # Reporting runs quarterly up to the present for a work still underway.
        # Capping the count left the newest report months old on long-running
        # works, so PROGRESS_REPORTING_STALLED fired across the clean population.
        n_reports = max(1, span // 90)
        for r in range(n_reports):
            pct = round(progress * (r + 1) / n_reports, 1)
            db.add(
                ProgressReport(
                    work_id=w.work_id,
                    report_date=w.sanctioned_date + timedelta(days=90 * (r + 1)),
                    physical_progress_pct=pct,
                    remarks=rng.choice(
                        ["Work proceeding as scheduled.", "Materials on site.",
                         "Progress reviewed at block level.", "Awaiting departmental inspection."]
                    ),
                )
            )

        # Disbursement tracks progress closely in a clean work.
        disbursed_pct = max(0.0, min(100.0, progress + rng.uniform(-8, 8)))
        installments = 1 if disbursed_pct < 40 else (2 if disbursed_pct < 80 else 3)
        for n in range(installments):
            db.add(
                Payment(
                    work_id=w.work_id,
                    installment_no=n + 1,
                    amount=round(w.estimated_cost * (disbursed_pct / 100) / installments, 2),
                    payment_date=w.sanctioned_date + timedelta(days=60 * (n + 1)),
                    reported_physical_progress_pct=round(progress * (n + 1) / installments, 1),
                )
            )

        # Photographs, geotagged at the site.
        stages = [PhotoStage.START]
        if progress > 45:
            stages.append(PhotoStage.MID)
        if w.status == WorkStatus.COMPLETED:
            stages.append(PhotoStage.COMPLETE)
        for stage in stages:
            plat, plon = jitter_point(rng, w.latitude, w.longitude, 0.05)
            captured = w.sanctioned_date + timedelta(days=rng.randint(20, max(21, span)))
            db.add(
                CompletionPhoto(
                    work_id=w.work_id,
                    upload_date=captured + timedelta(days=rng.randint(0, 6)),
                    capture_timestamp=datetime.combine(captured, datetime.min.time())
                    + timedelta(hours=rng.randint(7, 17)),
                    photo_lat=plat,
                    photo_lon=plon,
                    stage=stage,
                    image_hash=image_hash(f"{w.work_id}-{stage}"),
                    storage_path=f"synthetic/{w.work_id}/{stage.lower()}.jpg",
                )
            )

        # A completed work is normally handed over within a few weeks.
        if w.status == WorkStatus.COMPLETED and w.actual_completion_date:
            pool = user_agencies_by_district[w.district_id]
            if pool:
                ua = rng.choice(pool)
                initiated = w.actual_completion_date + timedelta(days=rng.randint(3, 20))
                acknowledged = initiated + timedelta(days=rng.randint(2, 14))
                db.add(
                    AssetHandover(
                        work_id=w.work_id,
                        user_agency_id=ua.user_agency_id,
                        handover_initiated_date=initiated,
                        handover_acknowledged_date=acknowledged,
                        uc_submitted_date=w.actual_completion_date + timedelta(days=rng.randint(5, 26)),
                        register_entry_date=acknowledged + timedelta(days=rng.randint(1, 9)),
                        status=HandoverStatus.ACKNOWLEDGED,
                    )
                )
                if (REFERENCE_DATE - acknowledged).days > 180:
                    if rng.random() < 0.12:
                        db.add(
                            MaintenanceRecommendation(
                                work_id=w.work_id,
                                user_agency_id=ua.user_agency_id,
                                raised_date=acknowledged + timedelta(days=rng.randint(120, 400)),
                                description=rng.choice(
                                    [
                                        "Roof sheeting has come loose at two corners and leaks during rain.",
                                        "Hand pump handle broken; the platform has developed cracks.",
                                        "Drain is silted along a 30 metre stretch and overflows.",
                                        "Two street light fittings have failed and need replacement.",
                                        "Boundary wall plaster is spalling on the northern face.",
                                    ]
                                ),
                                photo_reference=f"synthetic/{w.work_id}/maintenance.jpg",
                                status="OPEN",
                            )
                        )
                    db.add(
                        LifecycleCheckin(
                            work_id=w.work_id,
                            checkin_date=acknowledged + timedelta(days=180),
                            photo_reference=f"synthetic/{w.work_id}/checkin-6m.jpg",
                            still_in_use=rng.random() > 0.06,
                            notes="Six-month check-in recorded by the user agency.",
                        )
                    )


# ---------------------------------------------------------------------------
# Anomaly planting
# ---------------------------------------------------------------------------

PER_WORK_ANOMALIES = [
    PlantedAnomaly.COST_INFLATION,
    PlantedAnomaly.PAYMENT_AHEAD,
    PlantedAnomaly.GEOTAG_MISMATCH,
    PlantedAnomaly.TIMELINE_BREACH,
    PlantedAnomaly.COST_OVERRUN,
    PlantedAnomaly.GHOST_WORK,
    PlantedAnomaly.HANDOVER_GAP,
]

STRUCTURAL_ANOMALIES = [
    PlantedAnomaly.DUPLICATE_WORK,
    PlantedAnomaly.SALAMI_SLICING,
    PlantedAnomaly.PHOTO_REUSE,
    PlantedAnomaly.ENTITLEMENT_BREACH,
    PlantedAnomaly.QUOTA_SHORTFALL,
]

ALL_ANOMALIES = PER_WORK_ANOMALIES + STRUCTURAL_ANOMALIES


def target_counts(total_works: int) -> dict:
    """How many instances of each anomaly to plant.

    Split evenly with a floor per type. Recall computed over five instances is
    noise, so the floor matters more than matching the headline 12% exactly on
    a small dataset.
    """
    budget = max(int(total_works * ANOMALY_SHARE), MIN_PER_ANOMALY * len(ALL_ANOMALIES))
    per = max(MIN_PER_ANOMALY, budget // len(ALL_ANOMALIES))
    return {a: per for a in ALL_ANOMALIES}


def plant_per_work(db: Session, rng: random.Random, works: list[Work], targets: dict) -> None:
    """Anomalies that alter a single record."""
    by_district = {d.district_id: d for d in db.scalars(select(District)).all()}
    available = [w for w in works if w.planted_anomaly is None]
    rng.shuffle(available)
    pool = iter(available)

    def take(predicate=lambda w: True):
        for w in pool:
            if w.planted_anomaly is None and predicate(w):
                return w
        return None

    # COST_INFLATION - estimate far above the same-year benchmark.
    # Screened by Stage 1, so it must land on a work still awaiting sanction.
    for _ in range(targets[PlantedAnomaly.COST_INFLATION]):
        w = take(lambda w: w.status == WorkStatus.RECOMMENDED)
        if not w:
            break
        district = by_district[w.district_id]
        base = cat.WORK_TYPES[w.work_type][1]
        year = min(w.recommended_date.year, max(cat.SOR_YEARS))
        benchmark = sor_rate(base, year, district.terrain_category)
        w.estimated_cost = round(benchmark * rng.uniform(1.35, 2.20), 2)
        w.planted_anomaly = PlantedAnomaly.COST_INFLATION

    # PAYMENT_AHEAD - money released well beyond reported progress.
    for _ in range(targets[PlantedAnomaly.PAYMENT_AHEAD]):
        w = take(lambda w: w.sanctioned_date is not None and w.status != WorkStatus.COMPLETED)
        if not w:
            break
        reports = db.scalars(select(ProgressReport).where(ProgressReport.work_id == w.work_id)).all()
        progress = max((r.physical_progress_pct for r in reports), default=15.0)
        gap = rng.uniform(30, 60)
        disbursed = min(100.0, progress + gap)
        # Clamping at 100% would quietly shrink the gap below the planted range,
        # so pull reported progress down instead and keep the gap intact.
        progress = round(disbursed - gap, 1)
        for r in reports:
            r.physical_progress_pct = min(r.physical_progress_pct, progress)
        db.execute(delete(Payment).where(Payment.work_id == w.work_id))
        for n in range(2):
            db.add(
                Payment(
                    work_id=w.work_id,
                    installment_no=n + 1,
                    amount=round(w.estimated_cost * (disbursed / 100) / 2, 2),
                    payment_date=w.sanctioned_date + timedelta(days=45 * (n + 1)),
                    reported_physical_progress_pct=round(progress, 1),
                )
            )
        w.planted_anomaly = PlantedAnomaly.PAYMENT_AHEAD

    # GEOTAG_MISMATCH - photograph taken kilometres from the site.
    for _ in range(targets[PlantedAnomaly.GEOTAG_MISMATCH]):
        w = take(lambda w: w.sanctioned_date is not None)
        if not w:
            break
        photos = db.scalars(select(CompletionPhoto).where(CompletionPhoto.work_id == w.work_id)).all()
        if not photos:
            continue
        photo = rng.choice(photos)
        photo.photo_lat, photo.photo_lon = offset_point(
            w.latitude, w.longitude, rng.uniform(2_000, 40_000), rng.uniform(0, 360)
        )
        w.planted_anomaly = PlantedAnomaly.GEOTAG_MISMATCH

    # TIMELINE_BREACH - slow sanction, or long overdue completion.
    for _ in range(targets[PlantedAnomaly.TIMELINE_BREACH]):
        w = take(lambda w: w.sanctioned_date is not None and w.status != WorkStatus.COMPLETED)
        if not w:
            break
        if rng.random() < 0.5:
            w.sanctioned_date = w.recommended_date + timedelta(days=rng.randint(52, 190))
        else:
            w.sanctioned_date = REFERENCE_DATE - timedelta(days=rng.randint(400, 900))
            w.expected_completion_date = w.sanctioned_date + timedelta(days=365)
        w.planted_anomaly = PlantedAnomaly.TIMELINE_BREACH

    # COST_OVERRUN - final cost far above estimate, no revision recorded.
    for _ in range(targets[PlantedAnomaly.COST_OVERRUN]):
        w = take(lambda w: w.status == WorkStatus.COMPLETED)
        if not w:
            break
        w.final_cost = round(w.estimated_cost * rng.uniform(1.25, 1.80), 2)
        w.planted_anomaly = PlantedAnomaly.COST_OVERRUN

    # GHOST_WORK - fully paid, marked complete, no evidence of any kind.
    for _ in range(targets[PlantedAnomaly.GHOST_WORK]):
        w = take(lambda w: w.status == WorkStatus.COMPLETED)
        if not w:
            break
        for model in (ProgressReport, CompletionPhoto, AssetHandover, LifecycleCheckin, Payment):
            db.execute(delete(model).where(model.work_id == w.work_id))
        db.add(
            Payment(
                work_id=w.work_id,
                installment_no=1,
                amount=w.estimated_cost,
                payment_date=w.sanctioned_date + timedelta(days=40),
                reported_physical_progress_pct=100.0,
            )
        )
        w.final_cost = w.estimated_cost
        w.planted_anomaly = PlantedAnomaly.GHOST_WORK

    # HANDOVER_GAP - completed long ago, never handed over on paper.
    for _ in range(targets[PlantedAnomaly.HANDOVER_GAP]):
        w = take(
            lambda w: w.status == WorkStatus.COMPLETED
            and w.actual_completion_date is not None
            and (REFERENCE_DATE - w.actual_completion_date).days > 45
        )
        if not w:
            break
        db.execute(delete(AssetHandover).where(AssetHandover.work_id == w.work_id))
        db.execute(delete(LifecycleCheckin).where(LifecycleCheckin.work_id == w.work_id))
        w.planted_anomaly = PlantedAnomaly.HANDOVER_GAP


def plant_structural(
    db: Session, rng: random.Random, works: list[Work], targets: dict, ref: dict
) -> None:
    """Anomalies that only exist in the relationship between several records."""
    by_district = {d.district_id: d for d in ref["districts"]}
    agencies_by_district = defaultdict(list)
    for a in ref["agencies"]:
        agencies_by_district[a.district_id].append(a)

    # Candidates are pooled per district so a duplicate pair or a split cluster
    # never straddles two districts, which would contradict the work IDs.
    per_district: dict[str, list[Work]] = defaultdict(list)
    for w in works:
        if w.planted_anomaly is None:
            per_district[w.district_id].append(w)
    for bucket in per_district.values():
        rng.shuffle(bucket)
    cursors: dict[str, int] = defaultdict(int)

    def take(predicate=lambda w: True, district: str | None = None):
        keys = [district] if district else list(per_district)
        rng.shuffle(keys) if district is None else None
        for key in keys:
            bucket = per_district[key]
            while cursors[key] < len(bucket):
                w = bucket[cursors[key]]
                cursors[key] += 1
                if w.planted_anomaly is None and predicate(w):
                    return w
        return None

    # DUPLICATE_WORK - a near-copy close by and close in time.
    # Only the later work is labelled: it is the one a screener should catch,
    # with the earlier work as the thing it matches against.
    for _ in range(targets[PlantedAnomaly.DUPLICATE_WORK]):
        original = take(lambda w: w.recommended_date is not None)
        if not original:
            break
        # The copy is the work a screener should catch, so it must be the one
        # still awaiting sanction.
        copy = take(
            lambda w: w.status == WorkStatus.RECOMMENDED, district=original.district_id
        )
        if not copy:
            break
        copy.work_type = original.work_type
        copy.district_id = original.district_id
        copy.block = original.block
        copy.panchayat = original.panchayat
        # Same work described slightly differently, as two officers would write it.
        copy.description = original.description.replace(
            "Construction of", "Providing and laying"
        ).replace("Development of", "Construction of")
        copy.latitude, copy.longitude = offset_point(
            original.latitude, original.longitude, rng.uniform(40, 380), rng.uniform(0, 360)
        )
        copy.recommended_date = original.recommended_date + timedelta(days=rng.randint(10, 175))
        copy.estimated_cost = round(original.estimated_cost * rng.uniform(0.94, 1.07), 2)
        copy.planted_anomaly = PlantedAnomaly.DUPLICATE_WORK

    # SALAMI_SLICING - one job split into several just-under-threshold works.
    clusters = max(1, targets[PlantedAnomaly.SALAMI_SLICING] // 4)
    for _ in range(clusters):
        anchor = take(lambda w: w.status == WorkStatus.RECOMMENDED)
        if not anchor:
            break
        district = by_district[anchor.district_id]
        agency = rng.choice(agencies_by_district[anchor.district_id])
        threshold = rng.choice(cat.SANCTION_THRESHOLDS)
        members = [anchor]
        for _ in range(rng.randint(3, 6) - 1):
            m = take(lambda w: w.status == WorkStatus.RECOMMENDED, district=anchor.district_id)
            if m:
                members.append(m)
        for idx, m in enumerate(members):
            m.district_id = district.district_id
            m.block = anchor.block
            m.panchayat = anchor.panchayat
            m.work_type = anchor.work_type
            m.agency_id = agency.agency_id
            m.latitude, m.longitude = offset_point(
                anchor.latitude, anchor.longitude, rng.uniform(20, 260), rng.uniform(0, 360)
            )
            m.recommended_date = anchor.recommended_date + timedelta(days=rng.randint(0, 85))
            # Each priced just inside the threshold - the signature of a split job.
            m.estimated_cost = round(threshold * rng.uniform(0.90, 0.99), 2)
            m.description = (
                f"{rng.choice(cat.DESC_ACTION)} "
                f"{rng.choice(cat.DESC_DETAIL.get(m.work_type, ['public utility work']))} "
                f"at {anchor.panchayat}, segment {idx + 1} of {len(members)}."
            )
            m.planted_anomaly = PlantedAnomaly.SALAMI_SLICING

    # PHOTO_REUSE - one photograph submitted against two different works.
    for _ in range(targets[PlantedAnomaly.PHOTO_REUSE]):
        donor = take(lambda w: w.sanctioned_date is not None)
        borrower = take(lambda w: w.sanctioned_date is not None)
        if not donor or not borrower:
            break
        donor_photos = db.scalars(
            select(CompletionPhoto).where(CompletionPhoto.work_id == donor.work_id)
        ).all()
        borrower_photos = db.scalars(
            select(CompletionPhoto).where(CompletionPhoto.work_id == borrower.work_id)
        ).all()
        if not donor_photos or not borrower_photos:
            continue
        borrower_photos[0].image_hash = donor_photos[0].image_hash
        borrower.planted_anomaly = PlantedAnomaly.PHOTO_REUSE
        # Once the hash is shared, nothing in the record says which work is the
        # original, so the engine flags both - correctly. Both belong in the key.
        donor.planted_anomaly = PlantedAnomaly.PHOTO_REUSE

    # ENTITLEMENT_BREACH - a member's financial year pushed past the annual cap.
    breached = 0
    for mp in ref["mps"]:
        if breached >= targets[PlantedAnomaly.ENTITLEMENT_BREACH]:
            break
        mp_works = [
            w
            for w in works
            if w.mp_id == mp.mp_id and w.recommended_date and w.planted_anomaly is None
        ]
        by_fy = defaultdict(list)
        for w in mp_works:
            by_fy[financial_year_of(w.recommended_date)].append(w)
        if not by_fy:
            continue
        _, fy_works = max(by_fy.items(), key=lambda kv: len(kv[1]))
        if len(fy_works) < 4:
            continue
        total = sum(w.estimated_cost for w in fy_works)
        # Scale that year so the cumulative total lands just over the cap.
        factor = (mp.annual_entitlement * rng.uniform(1.03, 1.18)) / total
        for w in fy_works:
            w.estimated_cost = round(w.estimated_cost * factor, 2)
            w.planted_anomaly = PlantedAnomaly.ENTITLEMENT_BREACH
        breached += len(fy_works)

    # QUOTA_SHORTFALL - a district-year below the mandated SC/ST allocation.
    shortfall = 0
    for district in ref["districts"]:
        if shortfall >= targets[PlantedAnomaly.QUOTA_SHORTFALL]:
            break
        d_works = [
            w
            for w in works
            if w.district_id == district.district_id
            and w.recommended_date
            and financial_year_of(w.recommended_date) == 2025
            and w.planted_anomaly is None
        ]
        if len(d_works) < 8:
            continue
        # Strip the designation so the year closes below 15 percent / 7.5 percent.
        for w in d_works:
            w.is_sc_st_area = False
            w.planted_anomaly = PlantedAnomaly.QUOTA_SHORTFALL
        shortfall += len(d_works)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

TABLES_IN_DELETE_ORDER = [
    "agency_responses", "flag_reviews", "risk_flags", "module_contributions",
    "risk_assessments", "maintenance_recommendations", "lifecycle_checkins",
    "asset_handovers", "completion_photos", "progress_reports", "payments",
    "works", "users", "user_agencies", "agencies", "mps", "sor_benchmarks",
    "cost_index", "districts", "engine_config",
]


def reset(db: Session) -> None:
    """Clear every row, children before parents."""
    for table in TABLES_IN_DELETE_ORDER:
        db.execute(text(f"DELETE FROM {table}"))
    db.commit()


def count_of(db: Session, model) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


def report(db: Session) -> None:
    total = count_of(db, Work)
    print("")
    for label, model in [
        ("works", Work), ("districts", District), ("members", MP), ("agencies", Agency),
        ("user agencies", UserAgency), ("SoR rows", SORBenchmark), ("payments", Payment),
        ("progress reports", ProgressReport), ("photographs", CompletionPhoto),
        ("handovers", AssetHandover), ("users", User),
    ]:
        print(f"  {label:20} {count_of(db, model)}")

    print("\n  planted anomalies")
    planted = 0
    for a in ALL_ANOMALIES:
        n = db.scalar(
            select(func.count()).select_from(Work).where(Work.planted_anomaly == a)
        ) or 0
        planted += n
        print(f"    {a.value:22} {n}")
    pct = (planted / total * 100) if total else 0
    print(f"    {'TOTAL':22} {planted}   ({pct:.1f}% of works)")

    print("\n  status mix")
    for status in WorkStatus:
        n = db.scalar(select(func.count()).select_from(Work).where(Work.status == status)) or 0
        if n:
            print(f"    {status.value:22} {n}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the synthetic MPLADS dataset.")
    parser.add_argument("--works", type=int, default=4000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--reset", action="store_true", help="clear existing rows first")
    args = parser.parse_args()

    rng = random.Random(args.seed)

    with SessionLocal() as db:
        if args.reset:
            print("  clearing existing rows...")
            reset(db)

        print(f"  seeding reference data (seed={args.seed})...")
        ref = seed_reference(db, rng)
        seed_users(db, ref)
        version = seed_engine_config(db)

        print(f"  building {args.works} works...")
        works = build_works(db, rng, ref, args.works)

        print("  building payments, reports, photographs, handovers...")
        build_downstream(db, rng, works, ref)
        db.flush()

        targets = target_counts(args.works)
        print(f"  planting {len(ALL_ANOMALIES)} anomaly types, target {targets[ALL_ANOMALIES[0]]} each...")
        plant_per_work(db, rng, works, targets)
        plant_structural(db, rng, works, targets, ref)

        db.commit()
        print(f"\n  done. engine_version={version}, db_backend={settings.db_backend}")
        report(db)


if __name__ == "__main__":
    main()
