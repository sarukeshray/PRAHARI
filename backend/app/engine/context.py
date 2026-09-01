"""Everything the modules need, loaded once.

Scoring 4,000 works one at a time would issue tens of thousands of queries and
recompute the same peer statistics for every row. This object loads the reference
data, the per-work aggregates and the peer distributions in a handful of passes,
then hands modules plain dictionaries.

It is also where the peer groups are defined, which matters for fairness: an
agency is compared only against agencies working in the same terrain category,
never against a national average.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.engine.engine_config import Config, load_config
from app.models import (
    MP,
    Agency,
    AssetHandover,
    CompletionPhoto,
    District,
    Payment,
    ProgressReport,
    SORBenchmark,
    Work,
)
from app.models.enums import Terrain, WorkStatus

# The dataset's "today". Matches the generator so ages and overdue windows are
# measured from the same instant the data was built around.
REFERENCE_DATE = date(2026, 8, 31)

MPLADS_PERMISSIBLE_WORK_TYPES = {
    "ROAD_CC", "ROAD_BT", "COMMUNITY_HALL", "SCHOOL_BUILDING", "WATER_TANK",
    "BOREWELL", "STREET_LIGHTING", "DRAINAGE", "TOILET_BLOCK", "LIBRARY",
    "BUS_SHELTER", "CREMATORIUM_SHED",
}


@dataclass
class WorkAggregates:
    """Downstream totals for one work."""

    disbursed: float = 0.0
    latest_progress: float = 0.0
    report_count: int = 0
    last_report_date: date | None = None
    photo_count: int = 0


@dataclass
class AgencyStats:
    completed: int = 0
    total: int = 0
    mean_delay_days: float = 0.0
    mean_overrun_pct: float = 0.0
    completion_rate: float = 0.0
    percentile: float = 50.0
    peer_count: int = 0


@dataclass
class EngineContext:
    config: Config
    reference_date: date = REFERENCE_DATE

    districts: dict[str, District] = field(default_factory=dict)
    agencies: dict[str, Agency] = field(default_factory=dict)
    mps: dict[str, MP] = field(default_factory=dict)

    # (state, work_type, year, terrain) -> rate
    sor: dict[tuple, float] = field(default_factory=dict)
    sor_years: list[int] = field(default_factory=list)

    aggregates: dict[str, WorkAggregates] = field(default_factory=dict)
    photos: dict[str, list[CompletionPhoto]] = field(default_factory=lambda: defaultdict(list))

    # (work_type, terrain) -> (median cost ratio, MAD, n)
    peer_cost: dict[tuple, tuple[float, float, int]] = field(default_factory=dict)

    agency_stats: dict[str, AgencyStats] = field(default_factory=dict)

    # (mp_id, financial_year) -> cumulative recommended value
    mp_year_totals: dict[tuple, float] = field(default_factory=dict)

    # (district_id, financial_year) -> (sc/st value, total value)
    district_quota: dict[tuple, tuple[float, float]] = field(default_factory=dict)

    #: Works recommended after their member's year had already crossed the cap.
    #: An entitlement breach is a fact about a year, but it is *caused* by the
    #: works recommended past the line - flagging all 77 works in the year
    #: produced 1,307 findings for 17 facts and buried the signal.
    entitlement_breach_works: set[str] = field(default_factory=set)

    #: (district_id, fy) -> the one work that carries the quota finding.
    #: A shortfall is a property of a district's year, not of any single work,
    #: so it is raised once rather than against every work in that year.
    quota_carrier: dict[tuple, str] = field(default_factory=dict)

    # image hash -> the works it appears against
    photo_hash_index: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))

    handovers: dict[str, AssetHandover] = field(default_factory=dict)

    # Works grouped by district, for the duplicate and split searches.
    works_by_district: dict[str, list[Work]] = field(default_factory=lambda: defaultdict(list))

    def benchmark(self, work: Work) -> tuple[float, int] | None:
        """Schedule of Rates for a work, at the rate for its own year.

        Returning the year alongside the rate lets the explanation say which
        edition it compared against, which is the whole basis of the inflation
        defence — a cost is never compared to a rate from a different year.
        """
        district = self.districts[work.district_id]
        basis = work.recommended_date or work.sanctioned_date or self.reference_date
        year = min(max(basis.year, min(self.sor_years)), max(self.sor_years))
        rate = self.sor.get((district.state, work.work_type, year, district.terrain_category))
        return (rate, year) if rate is not None else None


def financial_year_of(d: date) -> int:
    return d.year if d.month >= 4 else d.year - 1


def build_context(db: Session, reference_date: date = REFERENCE_DATE) -> EngineContext:
    ctx = EngineContext(config=load_config(db), reference_date=reference_date)

    ctx.districts = {d.district_id: d for d in db.scalars(select(District)).all()}
    ctx.agencies = {a.agency_id: a for a in db.scalars(select(Agency)).all()}
    ctx.mps = {m.mp_id: m for m in db.scalars(select(MP)).all()}

    for row in db.scalars(select(SORBenchmark)).all():
        ctx.sor[(row.state, row.work_type, row.year, row.terrain_category)] = row.unit_rate
    ctx.sor_years = sorted({k[2] for k in ctx.sor})

    works = db.scalars(select(Work)).all()
    for w in works:
        ctx.works_by_district[w.district_id].append(w)
        ctx.aggregates[w.work_id] = WorkAggregates()

    # --- per-work aggregates, three grouped queries rather than 3N ---
    for work_id, total in db.execute(
        select(Payment.work_id, func.sum(Payment.amount)).group_by(Payment.work_id)
    ):
        ctx.aggregates[work_id].disbursed = float(total or 0)

    for work_id, latest, count_, last_date in db.execute(
        select(
            ProgressReport.work_id,
            func.max(ProgressReport.physical_progress_pct),
            func.count(),
            func.max(ProgressReport.report_date),
        ).group_by(ProgressReport.work_id)
    ):
        agg = ctx.aggregates[work_id]
        agg.latest_progress = float(latest or 0)
        agg.report_count = int(count_ or 0)
        agg.last_report_date = last_date if isinstance(last_date, date) else (
            date.fromisoformat(last_date) if last_date else None
        )

    for photo in db.scalars(select(CompletionPhoto)).all():
        ctx.photos[photo.work_id].append(photo)
        ctx.aggregates[photo.work_id].photo_count += 1
        ctx.photo_hash_index[photo.image_hash].add(photo.work_id)

    for h in db.scalars(select(AssetHandover)).all():
        ctx.handovers[h.work_id] = h

    _build_peer_costs(ctx, works)
    _build_agency_stats(ctx, works)
    _build_entitlement_and_quota(ctx, works)
    return ctx


def _build_peer_costs(ctx: EngineContext, works: list[Work]) -> None:
    """Median and MAD of the cost-to-benchmark ratio, per work type and terrain.

    The statistic is the *ratio*, not the rupee amount. Comparing rupee amounts
    across years would make every recent work look expensive simply because rates
    escalate; the ratio is already inflation-neutral, so the peer distribution is
    stable over the whole period.

    Median and MAD rather than mean and standard deviation because the thing
    being detected is an outlier, and outliers drag a mean towards themselves.
    """
    grouped: dict[tuple, list[float]] = defaultdict(list)
    for w in works:
        bench = ctx.benchmark(w)
        if not bench or bench[0] <= 0:
            continue
        district = ctx.districts[w.district_id]
        grouped[(w.work_type, district.terrain_category)].append(w.estimated_cost / bench[0])

    for key, ratios in grouped.items():
        if len(ratios) < 8:
            continue
        median = statistics.median(ratios)
        mad = statistics.median([abs(r - median) for r in ratios])
        ctx.peer_cost[key] = (median, mad, len(ratios))


def _build_agency_stats(ctx: EngineContext, works: list[Work]) -> None:
    """Agency record, ranked only within its own terrain peer group.

    An agency working in remote terrain will show more delay and more variance
    for entirely legitimate reasons. Ranking it nationally would convert that
    into a permanent penalty and, because the score feeds future scrutiny, into a
    feedback loop. Ranking within terrain is what stops that.
    """
    per_agency: dict[str, list[Work]] = defaultdict(list)
    for w in works:
        if w.agency_id:
            per_agency[w.agency_id].append(w)

    raw: dict[str, AgencyStats] = {}
    for agency_id, agency_works in per_agency.items():
        completed = [w for w in agency_works if w.status == WorkStatus.COMPLETED]
        delays, overruns = [], []
        for w in completed:
            if w.actual_completion_date and w.expected_completion_date:
                delays.append((w.actual_completion_date - w.expected_completion_date).days)
            if w.final_cost and w.estimated_cost:
                overruns.append((w.final_cost - w.estimated_cost) / w.estimated_cost * 100)
        raw[agency_id] = AgencyStats(
            completed=len(completed),
            total=len(agency_works),
            mean_delay_days=statistics.fmean(delays) if delays else 0.0,
            mean_overrun_pct=statistics.fmean(overruns) if overruns else 0.0,
            completion_rate=len(completed) / len(agency_works) if agency_works else 0.0,
        )

    # Rank inside each terrain group.
    by_terrain: dict[Terrain, list[str]] = defaultdict(list)
    for agency_id in raw:
        agency = ctx.agencies.get(agency_id)
        if agency:
            by_terrain[ctx.districts[agency.district_id].terrain_category].append(agency_id)

    for terrain, ids in by_terrain.items():
        # A single composite of the three signals, all oriented so higher is better.
        def quality(aid: str) -> float:
            s = raw[aid]
            return s.completion_rate * 100 - s.mean_delay_days * 0.10 - s.mean_overrun_pct

        ordered = sorted(ids, key=quality)
        n = len(ordered)
        for rank, aid in enumerate(ordered):
            raw[aid].percentile = ((rank + 0.5) / n) * 100 if n else 50.0
            raw[aid].peer_count = n

    ctx.agency_stats = raw


def _build_entitlement_and_quota(ctx: EngineContext, works: list[Work]) -> None:
    mp_totals: dict[tuple, float] = defaultdict(float)
    quota: dict[tuple, list[float]] = defaultdict(lambda: [0.0, 0.0])
    mp_year_works: dict[tuple, list[Work]] = defaultdict(list)
    district_year_works: dict[tuple, list[Work]] = defaultdict(list)

    for w in works:
        if not w.recommended_date:
            continue
        fy = financial_year_of(w.recommended_date)
        if w.mp_id:
            mp_totals[(w.mp_id, fy)] += w.estimated_cost
            mp_year_works[(w.mp_id, fy)].append(w)
        bucket = quota[(w.district_id, fy)]
        bucket[1] += w.estimated_cost
        if w.is_sc_st_area:
            bucket[0] += w.estimated_cost
        district_year_works[(w.district_id, fy)].append(w)

    ctx.mp_year_totals = dict(mp_totals)
    ctx.district_quota = {k: (v[0], v[1]) for k, v in quota.items()}

    # Walk each member-year in recommendation order and mark everything after
    # the cumulative total crosses the entitlement.
    for (mp_id, _fy), group in mp_year_works.items():
        entitlement = ctx.mps[mp_id].annual_entitlement if mp_id in ctx.mps else 50_000_000
        running = 0.0
        for w in sorted(group, key=lambda x: (x.recommended_date, x.work_id)):
            running += w.estimated_cost
            if running > entitlement:
                ctx.entitlement_breach_works.add(w.work_id)

    # One carrier per district-year: the latest non-SC/ST work, since that is
    # the most recent decision that could have gone the other way.
    for key, group in district_year_works.items():
        candidates = [w for w in group if not w.is_sc_st_area]
        if candidates:
            latest = max(candidates, key=lambda x: (x.recommended_date, x.work_id))
            ctx.quota_carrier[key] = latest.work_id
