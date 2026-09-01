"""Every flag code must have an explanation a reviewer can check.

The engine raises a flag code; the interface renders whatever template matches.
A code with no template, or a template referencing a parameter the module never
supplies, produces a finding nobody can act on - so both are failures here rather
than surprises in front of a District Officer.
"""

from __future__ import annotations

import re

import pytest

from app.engine import explain

# Codes that any module can emit, gathered from the module sources.
EMITTED_CODES = {
    "COST_ABOVE_SOR", "COST_BELOW_SOR", "COST_PEER_OUTLIER",
    "DUPLICATE_CANDIDATE", "SPLIT_WORK_PATTERN",
    "AGENCY_HISTORICAL_CONCERN",
    "WORK_TYPE_NOT_PERMISSIBLE", "ENTITLEMENT_EXCEEDED", "QUOTA_SHORTFALL",
    "OUT_OF_CONSTITUENCY", "SANCTION_DELAY_45D", "MISSING_RECOMMENDATION",
    "STATISTICAL_OUTLIER",
    "PAYMENT_AHEAD_OF_PROGRESS", "FULLY_PAID_INCOMPLETE",
    "PHOTO_LOCATION_MISMATCH", "PHOTO_TIMESTAMP_INVALID", "PHOTO_REUSED_ACROSS_WORKS",
    "COST_OVERRUN",
    "COMPLETION_OVERDUE_12M", "PROGRESS_REPORTING_STALLED",
    "NO_COMPLETION_EVIDENCE", "GHOST_WORK",
    "HANDOVER_OVERDUE", "UC_MISSING", "REGISTER_GAP",
}


def test_every_emitted_code_has_a_template():
    missing = sorted(EMITTED_CODES - set(explain.TEMPLATES))
    assert not missing, f"flag codes with no explanation template: {missing}"


def test_no_orphan_templates():
    orphans = sorted(set(explain.TEMPLATES) - EMITTED_CODES)
    assert not orphans, f"templates for codes no module emits: {orphans}"


@pytest.mark.parametrize("code", sorted(explain.TEMPLATES))
def test_every_template_names_a_number(code):
    """An explanation that cites no figure cannot be verified against the record."""
    template = explain.TEMPLATES[code]
    placeholders = set(re.findall(r"\{(\w+)", template))
    assert placeholders, f"{code} has no substituted values at all"


def test_missing_parameter_raises_rather_than_rendering_a_gap():
    with pytest.raises(KeyError, match="missing parameter"):
        explain.render("COST_ABOVE_SOR", {"estimated_cost": "Rs 1"})


def test_unknown_code_raises():
    with pytest.raises(KeyError, match="no explanation template"):
        explain.render("NOT_A_REAL_CODE", {})


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (0, "Rs 0"),
        (999, "Rs 999"),
        (1_000, "Rs 1,000"),
        (100_000, "Rs 1,00,000"),
        (1_820_000, "Rs 18,20,000"),
        (52_400_000, "Rs 5,24,00,000"),
    ],
)
def test_indian_digit_grouping(amount, expected):
    assert explain.rupees(amount) == expected
