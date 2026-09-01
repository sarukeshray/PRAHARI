"""Templated explanations, one per flag code.

Deterministic and generated from the computed signal values. No language model
sits anywhere in this path: a District Officer has to be able to check the
sentence against the record without asking a data scientist, and an explanation
that varies between runs cannot be audited.

Every template names the number that triggered the finding and the threshold it
crossed. A template that says only that something is unusual is a bug.
"""

from __future__ import annotations

TEMPLATES: dict[str, str] = {
    # --- Stage 1: COST -----------------------------------------------------
    "COST_ABOVE_SOR": (
        "Estimated cost of {estimated_cost} is {deviation_pct:.0f}% above the {state} "
        "Schedule of Rates benchmark of {benchmark} for {work_type} in {terrain} terrain "
        "({sor_year} rates)."
    ),
    "COST_BELOW_SOR": (
        "Estimated cost of {estimated_cost} is {deviation_abs:.0f}% below the {state} "
        "Schedule of Rates benchmark of {benchmark} for {work_type} in {terrain} terrain. "
        "An estimate this far under benchmark usually signals incomplete scope rather "
        "than a saving."
    ),
    "COST_PEER_OUTLIER": (
        "Cost sits {modified_z:.1f} median-absolute-deviations above the median for "
        "{work_type} works in {terrain} districts, across {peer_count} comparable works. "
        "The flagging threshold is {threshold:.1f}."
    ),
    # --- Stage 1: DUPLICATE ------------------------------------------------
    "DUPLICATE_CANDIDATE": (
        "Description is {similarity:.0%} similar to work {other_work_id} "
        "({other_description_short}), located {distance_m:.0f} m away and recommended "
        "{days_apart} days apart."
    ),
    "SPLIT_WORK_PATTERN": (
        "{cluster_size} works by {agency_name} fall within a {cluster_span_m:.0f} m cluster "
        "over {window_days} days, each estimated between {min_cost} and {max_cost} — "
        "just under the {threshold_label} sanction threshold, and together totalling "
        "{total_cost}."
    ),
    # --- Stage 1: AGENCY ---------------------------------------------------
    "AGENCY_HISTORICAL_CONCERN": (
        "Implementing agency ranks in the weakest {percentile:.0f}% among "
        "{peer_count} agencies operating in comparable {terrain} districts, based on "
        "{completed_count} completed works. This signal is peer-group relative and "
        "contributes at most {cap_pct:.0f}% of the score."
    ),
    # --- Stage 1: COMPLIANCE -----------------------------------------------
    "WORK_TYPE_NOT_PERMISSIBLE": (
        "Work type {work_type} is not on the MPLADS permissible works list. "
        "Recommendations must fall within the categories set out in the MPLADS "
        "Guidelines."
    ),
    "ENTITLEMENT_EXCEEDED": (
        "Recommendations by {mp_name} for FY {financial_year} total {cumulative}, against "
        "an annual entitlement of {entitlement} — an excess of {excess}."
    ),
    "QUOTA_SHORTFALL": (
        "{district} recorded {actual_pct:.1f}% of FY {financial_year} allocation in "
        "{quota_kind} areas, against the mandated {required_pct:.1f}%. "
        "{shortfall_amount} of the year's {total_amount} would need to be redirected to "
        "meet it."
    ),
    "OUT_OF_CONSTITUENCY": (
        "{mp_name} represents {constituency} in the Lok Sabha, but this work is located "
        "in {district} district. A Lok Sabha member may recommend works only within "
        "their own constituency."
    ),
    # One code, two situations: a decision still outstanding, or one taken late.
    # The sentence has to say which, because they call for different action.
    "SANCTION_DELAY_45D": (
        "Sanction was decided {days_elapsed} days after the recommendation. "
        "MPLADS Guidelines 2023 require a decision within {threshold:.0f} days."
    ),
    "MISSING_RECOMMENDATION": (
        "Work was sanctioned on {sanctioned_date} with no recommendation record against "
        "it. Every MPLADS work requires a recommendation from the Member before sanction."
    ),
    # --- Stage 1: STATISTICAL ----------------------------------------------
    "STATISTICAL_OUTLIER": (
        "Isolation Forest places this proposal among the {top_pct:.0f}% most unusual "
        "works in the district when cost, location density, agency record and Member "
        "workload are considered together (score {score:.0f}, flagging above "
        "{threshold:.0f})."
    ),
    # --- Stage 2: DISBURSEMENT ---------------------------------------------
    "PAYMENT_AHEAD_OF_PROGRESS": (
        "{disbursed_pct:.0f}% of sanctioned funds released against {progress_pct:.0f}% "
        "reported physical progress — a gap of {divergence:.0f} percentage points, "
        "against a threshold of {threshold:.0f}."
    ),
    "FULLY_PAID_INCOMPLETE": (
        "Full sanctioned amount of {estimated_cost} has been released, but reported "
        "physical progress stands at {progress_pct:.0f}%."
    ),
    # --- Stage 2: GEOTAG ---------------------------------------------------
    "PHOTO_LOCATION_MISMATCH": (
        "A {stage} photograph carries GPS coordinates {distance_km:.1f} km from the "
        "recorded work site, against a tolerance of {threshold_m:.0f} m. This is "
        "metadata verification only — the image itself has not been examined."
    ),
    "PHOTO_TIMESTAMP_INVALID": (
        "A {stage} photograph carries a capture timestamp of {captured}, which is "
        "{days_before} days before the work was sanctioned on {sanctioned_date}."
    ),
    "PHOTO_REUSED_ACROSS_WORKS": (
        "The same photograph has been submitted against {work_count} different works "
        "({other_work_ids}). Image fingerprints are identical."
    ),
    # --- Stage 2: VARIANCE -------------------------------------------------
    "COST_OVERRUN": (
        "Final cost of {final_cost} is {variance_pct:.0f}% above the estimated "
        "{estimated_cost}, with no revised estimate recorded against this work. "
        "The flagging threshold is {threshold:.0f}%."
    ),
    # --- Stage 2: TIMELINE -------------------------------------------------
    "COMPLETION_OVERDUE_12M": (
        "Sanctioned {days_since_sanction} days ago and reported {progress_pct:.0f}% "
        "complete. The MPLADS guideline for completion is {threshold_days:.0f} days "
        "from sanction."
    ),
    "PROGRESS_REPORTING_STALLED": (
        "No progress report has been filed for {days_since_report} days, against a "
        "threshold of {threshold:.0f}. The most recent report placed the work at "
        "{progress_pct:.0f}% complete."
    ),
    "NO_COMPLETION_EVIDENCE": (
        "Work is marked complete but carries no completion photograph. "
        "{report_count} progress reports are on file."
    ),
    "GHOST_WORK": (
        "Work is marked complete with {disbursed_pct:.0f}% of funds released, but has "
        "no progress reports and no photographs of any kind on file."
    ),
    # --- Stage 3: HANDOVER -------------------------------------------------
    "HANDOVER_OVERDUE": (
        "Work was completed {days_since_completion} days ago and no handover to a user "
        "agency has been {handover_state}. The threshold is {threshold_days:.0f} days. "
        "An asset with no recorded owner has nobody accountable for its upkeep."
    ),
    "UC_MISSING": (
        "No Utilisation Certificate has been recorded {days_since_completion} days after "
        "completion, against a requirement of {threshold_days:.0f} days."
    ),
    "REGISTER_GAP": (
        "Work was completed and handed over on {handover_date}, but no asset register "
        "entry has been recorded against it."
    ),
}


SANCTION_PENDING_TEMPLATE = (
    "Recommendation was received {days_elapsed} days ago and no sanction decision has "
    "been recorded. MPLADS Guidelines 2023 require a decision within {threshold:.0f} days."
)


def render(code: str, params: dict) -> str:
    """Fill the template for ``code``.

    A missing template raises rather than falling back to a generic sentence: a
    finding a reviewer cannot check is worse than no finding, and it should fail
    loudly in tests rather than quietly in production.
    """
    if code == "SANCTION_DELAY_45D" and not params.get("decided", True):
        return SANCTION_PENDING_TEMPLATE.format(**params)
    template = TEMPLATES.get(code)
    if template is None:
        raise KeyError(f"no explanation template for flag code {code!r}")
    try:
        return template.format(**params)
    except KeyError as exc:
        raise KeyError(f"explanation for {code!r} is missing parameter {exc}") from exc


def rupees(amount: float) -> str:
    """Indian digit grouping: 1820000 -> Rs 18,20,000."""
    n = int(round(amount))
    sign = "-" if n < 0 else ""
    s = str(abs(n))
    if len(s) <= 3:
        body = s
    else:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        body = ",".join(parts) + "," + tail
    return f"{sign}Rs {body}"


def all_codes() -> list[str]:
    return sorted(TEMPLATES)
