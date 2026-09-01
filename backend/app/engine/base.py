"""Shared types for every engine module.

A module answers one question about a work and returns a score plus zero or more
findings. It never decides anything, never writes to the database, and never
reads ``works.planted_anomaly`` — that column exists only to grade the engine
afterwards, and a module that peeked at it would be grading itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.enums import ModuleCode, SeverityTier


@dataclass(frozen=True)
class Finding:
    """One thing worth a person's attention, with the numbers that produced it.

    ``params`` carries whatever the explanation template for ``code`` needs. The
    template is looked up by code and filled deterministically — no language
    model sits anywhere in this path, because a reviewer has to be able to check
    the sentence against the record.
    """

    code: str
    module: ModuleCode
    signal_value: float
    threshold_value: float
    severity: SeverityTier
    params: dict = field(default_factory=dict)


@dataclass
class ModuleResult:
    """A module's verdict on one work."""

    module: ModuleCode
    score: float
    findings: list[Finding] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.score = max(0.0, min(100.0, float(self.score)))


def tier_from_exceedance(signal: float, threshold: float) -> SeverityTier:
    """Grade a finding by how far past its threshold the signal sits.

    A value barely over the line is a MEDIUM; one at nearly double the threshold
    is CRITICAL. Using the size of the breach rather than a fixed severity per
    code means a 26% cost deviation and a 120% one do not arrive looking equally
    urgent in a reviewer's queue.
    """
    if threshold == 0:
        return SeverityTier.HIGH
    exceedance = (abs(signal) - abs(threshold)) / abs(threshold)
    if exceedance < 0.25:
        return SeverityTier.MEDIUM
    if exceedance < 0.75:
        return SeverityTier.HIGH
    return SeverityTier.CRITICAL


def score_from_exceedance(signal: float, threshold: float, ceiling: float = 2.0) -> float:
    """Map a breach onto 0-100 for the composite.

    Sitting exactly on the threshold scores 50; ``ceiling`` times the threshold
    or beyond scores 100. Below the threshold the score decays towards zero, so a
    work well inside its limits contributes almost nothing rather than a floor of
    noise.
    """
    if threshold == 0:
        return 50.0
    ratio = abs(signal) / abs(threshold)
    if ratio <= 1.0:
        return max(0.0, 50.0 * ratio)
    span = max(ceiling - 1.0, 1e-6)
    return min(100.0, 50.0 + 50.0 * (ratio - 1.0) / span)


def worst(findings: list[Finding]) -> SeverityTier | None:
    """The most urgent tier among a set of findings."""
    if not findings:
        return None
    order = [SeverityTier.LOW, SeverityTier.MEDIUM, SeverityTier.HIGH, SeverityTier.CRITICAL]
    return max((f.severity for f in findings), key=order.index)
