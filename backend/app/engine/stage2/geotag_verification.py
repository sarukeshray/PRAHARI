"""GEOTAG — does the photographic evidence belong to this work?

**This is metadata verification, not image forensics.** Nothing here examines
pixels. It checks three things a photograph's own metadata can settle: where it
was taken, when it was taken, and whether the same file has been submitted twice.

That boundary is deliberate and worth stating to a reviewer: the module can say a
photograph's GPS is 6 km from the site, and it cannot say whether the photograph
has been edited.

The metadata is extracted server-side after upload, never accepted from the
client. The party submitting the photograph is the party this check exists to
verify, so trusting their copy of the EXIF would leave no control at all.
"""

from __future__ import annotations

from app.engine.base import Finding, ModuleResult, score_from_exceedance, tier_from_exceedance
from app.engine.context import EngineContext
from app.geo_utils import haversine_m
from app.models.enums import ModuleCode, SeverityTier
from app.models.works import Work

MODULE = ModuleCode.GEOTAG


def evaluate(work: Work, ctx: EngineContext) -> ModuleResult:
    photos = ctx.photos.get(work.work_id, [])
    if not photos:
        return ModuleResult(MODULE, 0.0, [])

    findings: list[Finding] = []
    scores: list[float] = []

    limit_m = ctx.config.t("PHOTO_DISTANCE_M")

    # --- 1. Location ---
    # Reported against the furthest offending photograph. One good photograph
    # does not answer a bad one, so the worst case is the finding.
    worst_distance = 0.0
    worst_photo = None
    for photo in photos:
        if photo.photo_lat is None or photo.photo_lon is None:
            continue
        distance = haversine_m(work.latitude, work.longitude, photo.photo_lat, photo.photo_lon)
        if distance > worst_distance:
            worst_distance, worst_photo = distance, photo

    if worst_photo is not None and worst_distance > limit_m:
        findings.append(
            Finding(
                code="PHOTO_LOCATION_MISMATCH",
                module=MODULE,
                signal_value=round(worst_distance, 1),
                threshold_value=limit_m,
                severity=tier_from_exceedance(worst_distance, limit_m),
                params={
                    "stage": worst_photo.stage.value.lower(),
                    "distance_km": worst_distance / 1000,
                    "threshold_m": limit_m,
                },
            )
        )
        scores.append(score_from_exceedance(worst_distance, limit_m, ceiling=10.0))

    # --- 2. Timestamp before sanction ---
    if work.sanctioned_date:
        for photo in photos:
            if photo.capture_timestamp is None:
                continue
            captured = photo.capture_timestamp.date()
            if captured < work.sanctioned_date:
                days_before = (work.sanctioned_date - captured).days
                findings.append(
                    Finding(
                        code="PHOTO_TIMESTAMP_INVALID",
                        module=MODULE,
                        signal_value=float(days_before),
                        threshold_value=0.0,
                        severity=SeverityTier.HIGH,
                        params={
                            "stage": photo.stage.value.lower(),
                            "captured": captured.strftime("%d %b %Y"),
                            "days_before": days_before,
                            "sanctioned_date": work.sanctioned_date.strftime("%d %b %Y"),
                        },
                    )
                )
                scores.append(75.0)
                break

    # --- 3. The same image against more than one work ---
    for photo in photos:
        others = ctx.photo_hash_index.get(photo.image_hash, set()) - {work.work_id}
        if others:
            listed = sorted(others)
            findings.append(
                Finding(
                    code="PHOTO_REUSED_ACROSS_WORKS",
                    module=MODULE,
                    signal_value=float(len(others) + 1),
                    threshold_value=1.0,
                    severity=SeverityTier.CRITICAL,
                    params={
                        "work_count": len(others) + 1,
                        "other_work_ids": ", ".join(listed[:3])
                        + (f" and {len(listed) - 3} more" if len(listed) > 3 else ""),
                    },
                )
            )
            scores.append(95.0)
            break

    return ModuleResult(MODULE, max(scores) if scores else 0.0, findings)
