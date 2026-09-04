"""DUPLICATE — is this work already funded, or is it one slice of a larger one?

Two distinct patterns.

**Duplicate.** The same work recommended twice. Caught by description similarity
combined with physical and temporal proximity. Similarity alone is useless here:
"Construction of CC road at X" describes thousands of legitimate works. It only
becomes a signal when the two are also metres apart and months apart.

**Split work.** One job divided into pieces that each sit just under a sanction
threshold. The signature is not any single work but the arrangement: several
works, one agency, one small area, one short window, each priced just inside a
round number.
"""

from __future__ import annotations

import math
from collections import defaultdict

from app.engine.base import Finding, ModuleResult, score_from_exceedance
from app.engine.context import EngineContext
from app.engine.explain import rupees
from app.engine.similarity import backend as similarity_backend
from app.engine.similarity import similarity as text_similarity
from app.geo_utils import haversine_m
from app.models.enums import ModuleCode, SeverityTier
from app.models.works import Work

MODULE = ModuleCode.DUPLICATE


def _short(text: str, words: int = 7) -> str:
    parts = text.split()
    return " ".join(parts[:words]) + ("..." if len(parts) > words else "")


def evaluate(work: Work, ctx: EngineContext) -> ModuleResult:
    findings: list[Finding] = []
    scores: list[float] = []

    if work.recommended_date is None:
        return ModuleResult(MODULE, 0.0, [])

    # The threshold follows the backend that produced the score. See the note in
    # weights.yaml: the two live on different scales.
    cos_limit = (
        ctx.config.t("DUPLICATE_COSINE_FALLBACK")
        if "fallback" in similarity_backend()
        else ctx.config.t("DUPLICATE_COSINE")
    )
    dist_limit = ctx.config.t("DUPLICATE_DISTANCE_M")
    window = ctx.config.t("DUPLICATE_WINDOW_DAYS")

    # Only works in the same district are candidates. Two works 500 m apart are
    # in the same district by definition, so this costs nothing in recall and
    # turns an O(n^2) sweep over the whole corpus into one over a few hundred.
    neighbours = ctx.works_by_district.get(work.district_id, [])

    best: tuple[float, Work, float, int] | None = None
    for other in neighbours:
        if other.work_id == work.work_id or other.recommended_date is None:
            continue
        if other.work_type != work.work_type:
            continue
        days_apart = abs((work.recommended_date - other.recommended_date).days)
        if days_apart > window:
            continue
        distance = haversine_m(work.latitude, work.longitude, other.latitude, other.longitude)
        if distance > dist_limit:
            continue
        sim = text_similarity(work.description, other.description)
        if sim < cos_limit:
            continue
        if best is None or sim > best[0]:
            best = (sim, other, distance, days_apart)

    if best:
        sim, other, distance, days_apart = best
        findings.append(
            Finding(
                code="DUPLICATE_CANDIDATE",
                module=MODULE,
                signal_value=round(sim, 4),
                threshold_value=cos_limit,
                severity=SeverityTier.CRITICAL if sim >= 0.92 else SeverityTier.HIGH,
                params={
                    "similarity": sim,
                    "other_work_id": other.work_id,
                    "other_description_short": _short(other.description),
                    "distance_m": distance,
                    "days_apart": days_apart,
                },
            )
        )
        scores.append(score_from_exceedance(sim, cos_limit, ceiling=1.22))

    split = _detect_split(work, ctx)
    if split:
        findings.append(split)
        scores.append(85.0)

    return ModuleResult(MODULE, max(scores) if scores else 0.0, findings)


def _detect_split(work: Work, ctx: EngineContext) -> Finding | None:
    """Look for a cluster this work belongs to that reads as one divided job."""
    if work.agency_id is None or work.recommended_date is None:
        return None

    eps = ctx.config.t("SPLIT_CLUSTER_EPS_M")
    min_works = int(ctx.config.t("SPLIT_MIN_WORKS"))
    window = ctx.config.t("SPLIT_WINDOW_DAYS")
    under_pct = ctx.config.t("SPLIT_UNDER_THRESHOLD_PCT")

    cluster = [
        other
        for other in ctx.works_by_district.get(work.district_id, [])
        if other.agency_id == work.agency_id
        and other.recommended_date is not None
        and abs((work.recommended_date - other.recommended_date).days) <= window
        and haversine_m(work.latitude, work.longitude, other.latitude, other.longitude) <= eps
    ]
    if len(cluster) < min_works:
        return None

    # Every member must sit just inside the same round threshold. A cluster of
    # genuinely small works scattered below a threshold is not a split job; works
    # bunched immediately beneath one is what the pattern looks like.
    thresholds = [500_000.0, 1_000_000.0, 2_500_000.0, 5_000_000.0]
    for threshold in thresholds:
        floor = threshold * (1 - under_pct / 100)
        members = [w for w in cluster if floor <= w.estimated_cost < threshold]
        if len(members) < min_works:
            continue

        costs = [w.estimated_cost for w in members]
        dates = sorted(w.recommended_date for w in members)
        span_m = max(
            haversine_m(a.latitude, a.longitude, b.latitude, b.longitude)
            for a in members
            for b in members
        )
        agency = ctx.agencies.get(work.agency_id)
        return Finding(
            code="SPLIT_WORK_PATTERN",
            module=MODULE,
            signal_value=float(len(members)),
            threshold_value=float(min_works),
            severity=SeverityTier.HIGH if len(members) < 5 else SeverityTier.CRITICAL,
            params={
                "cluster_size": len(members),
                "agency_name": agency.name if agency else work.agency_id,
                "cluster_span_m": span_m,
                "window_days": (dates[-1] - dates[0]).days,
                "min_cost": rupees(min(costs)),
                "max_cost": rupees(max(costs)),
                "threshold_label": rupees(threshold),
                "total_cost": rupees(sum(costs)),
            },
        )
    return None
