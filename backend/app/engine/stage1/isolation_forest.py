"""STATISTICAL — is this proposal unusual in combination, rather than on any one axis?

Isolation Forest, unsupervised. No labelled dataset of MPLADS irregularities
exists, so there is nothing to train a classifier against; this model learns what
the ordinary population looks like and reports how far a proposal sits from it.

It catches the case the rule modules cannot: a work whose cost is fine, whose
description is unique, whose agency is sound, but whose *combination* of
attributes appears almost nowhere else in the corpus.

Two design points that matter for reproducibility:

* Every feature is a ratio or a count, never a rupee amount. Raw cost would let
  the model learn "expensive work types are unusual", which is not a finding.
* Age is deliberately NOT a feature. The original specification listed
  ``days_recommendation_to_now``, but only works awaiting sanction reach Stage 1
  and those are all recent, so the model learned that recency is strange and
  flagged 39% of proposals. A work is not unusual for being new. Timeliness is
  a compliance rule with a stated threshold, which is where it belongs.
"""

from __future__ import annotations

import logging

import numpy as np

from app.engine.base import Finding, ModuleResult
from app.engine.context import EngineContext, financial_year_of
from app.geo_utils import haversine_m
from app.models.enums import ModuleCode, SeverityTier
from app.models.works import Work

logger = logging.getLogger(__name__)
MODULE = ModuleCode.STATISTICAL

FEATURE_NAMES = [
    "cost_ratio",
    "cost_peer_z",
    "agency_percentile",
    "works_by_mp_this_year",
    "works_in_500m",
    "is_sc_st_area",
]


class StatisticalModel:
    """Fitted once over the corpus, then applied to each work.

    Held as an object rather than module state so tests can fit a small model
    without touching a global.
    """

    def __init__(self) -> None:
        self.forest = None
        self.training_scores = None
        self.lo = 0.0
        self.hi = 1.0
        self.work_type_levels: list[str] = []
        self.terrain_levels: list[str] = []

    # -- feature construction ------------------------------------------------

    def features(self, work: Work, ctx: EngineContext) -> list[float]:
        district = ctx.districts[work.district_id]

        bench = ctx.benchmark(work)
        cost_ratio = work.estimated_cost / bench[0] if bench and bench[0] > 0 else 1.0

        peer = ctx.peer_cost.get((work.work_type, district.terrain_category))
        if peer and peer[1] > 0:
            cost_peer_z = 0.6745 * (cost_ratio - peer[0]) / peer[1]
        else:
            cost_peer_z = 0.0

        stats = ctx.agency_stats.get(work.agency_id) if work.agency_id else None
        agency_percentile = stats.percentile if stats else 50.0

        basis = work.recommended_date or work.sanctioned_date or ctx.reference_date
        fy = financial_year_of(basis)
        mp_count = sum(
            1
            for w in ctx.works_by_district.get(work.district_id, [])
            if w.mp_id == work.mp_id
            and w.recommended_date
            and financial_year_of(w.recommended_date) == fy
        )

        nearby = sum(
            1
            for w in ctx.works_by_district.get(work.district_id, [])
            if w.work_id != work.work_id
            and haversine_m(work.latitude, work.longitude, w.latitude, w.longitude) <= 500
        )

        numeric = [
            cost_ratio,
            cost_peer_z,
            agency_percentile,
            float(mp_count),
            float(nearby),
            1.0 if work.is_sc_st_area else 0.0,
        ]
        one_hot = [1.0 if work.work_type == t else 0.0 for t in self.work_type_levels]
        one_hot += [
            1.0 if district.terrain_category.value == t else 0.0 for t in self.terrain_levels
        ]
        return numeric + one_hot

    # -- fitting -------------------------------------------------------------

    def fit(self, works: list[Work], ctx: EngineContext) -> None:
        from sklearn.ensemble import IsolationForest

        self.work_type_levels = sorted({w.work_type for w in works})
        self.terrain_levels = sorted(
            {ctx.districts[w.district_id].terrain_category.value for w in works}
        )

        matrix = np.array([self.features(w, ctx) for w in works], dtype=float)
        contamination = ctx.config.t("ISOLATION_CONTAMINATION")

        self.forest = IsolationForest(
            n_estimators=200,
            contamination=contamination,
            random_state=42,
            n_jobs=-1,
        )
        self.forest.fit(matrix)

        # Rank rather than min-max. The specification called for min-max over
        # decision_function, but that distribution is tightly clustered: scaled
        # linearly, 4,000 works produced 6 above the flagging line and a score
        # of "78" corresponded to nothing a reader could name. Storing the
        # sorted training scores instead lets score() return a true percentile,
        # so 78 means "more unusual than 78% of the corpus" - which is exactly
        # what the explanation template asserts. See DECISIONS.md D-014.
        raw = self.forest.decision_function(matrix)
        self.training_scores = np.sort(raw)
        self.lo, self.hi = float(raw.min()), float(raw.max())

    def score(self, work: Work, ctx: EngineContext) -> float:
        """0-100 percentile of unusualness against the training distribution."""
        if self.forest is None or self.training_scores is None:
            return 0.0
        raw = float(self.forest.decision_function([self.features(work, ctx)])[0])
        # decision_function is higher for ordinary points, so the share of the
        # corpus scoring at or below this one is the share it is stranger than.
        rank = float(np.searchsorted(self.training_scores, raw, side="left"))
        return max(0.0, min(100.0, 100.0 - (rank / len(self.training_scores)) * 100.0))


def evaluate(work: Work, ctx: EngineContext, model: StatisticalModel | None) -> ModuleResult:
    if model is None or model.forest is None:
        return ModuleResult(MODULE, 0.0, [])

    score = model.score(work, ctx)
    limit = ctx.config.t("ISOLATION_SCORE_FLAG_AT")
    if score <= limit:
        return ModuleResult(MODULE, score, [])

    finding = Finding(
        code="STATISTICAL_OUTLIER",
        module=MODULE,
        signal_value=round(score, 2),
        threshold_value=limit,
        # Held at MEDIUM: a statistical oddity is a reason to look, not evidence
        # of anything. The rule modules carry the weight when something is wrong.
        severity=SeverityTier.MEDIUM,
        params={"score": score, "threshold": limit, "top_pct": max(1.0, 100.0 - score)},
    )
    return ModuleResult(MODULE, score, [finding])
