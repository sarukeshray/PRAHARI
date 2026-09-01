"""COMPLIANCE — deterministic rule checks against the MPLADS Guidelines.

Nothing here is inferred. Each check is a rule with a stated source, and each
returns the values that produced it. That is why a compliance finding lifts a
work to at least HIGH regardless of the weighted score: a rule violation is a
determinate fact, not a statistical suspicion.

Two of these checks apply after sanction as well as before, so the module runs in
Stage 2 too. It carries no weight there — the Stage 2 weights are left exactly as
specified — and acts purely through the tier override.
"""

from __future__ import annotations

from app.engine.base import Finding, ModuleResult
from app.engine.context import MPLADS_PERMISSIBLE_WORK_TYPES, EngineContext, financial_year_of
from app.engine.explain import rupees
from app.models.enums import House, ModuleCode, SeverityTier
from app.models.works import Work

MODULE = ModuleCode.COMPLIANCE


def _fy_label(fy: int) -> str:
    return f"{fy}-{str(fy + 1)[2:]}"


def evaluate(work: Work, ctx: EngineContext) -> ModuleResult:
    findings: list[Finding] = []
    district = ctx.districts[work.district_id]

    # --- 1. Work type must be on the permissible list ---
    if work.work_type not in MPLADS_PERMISSIBLE_WORK_TYPES:
        findings.append(
            Finding(
                code="WORK_TYPE_NOT_PERMISSIBLE",
                module=MODULE,
                signal_value=1.0,
                threshold_value=0.0,
                severity=SeverityTier.CRITICAL,
                params={"work_type": work.work_type},
            )
        )

    # --- 2. A sanction requires a recommendation behind it ---
    if work.recommended_date is None and work.sanctioned_date is not None:
        findings.append(
            Finding(
                code="MISSING_RECOMMENDATION",
                module=MODULE,
                signal_value=1.0,
                threshold_value=0.0,
                severity=SeverityTier.CRITICAL,
                params={"sanctioned_date": work.sanctioned_date.strftime("%d %b %Y")},
            )
        )

    if work.recommended_date is not None:
        fy = financial_year_of(work.recommended_date)

        # --- 3. Annual entitlement ---
        mp = ctx.mps.get(work.mp_id) if work.mp_id else None
        if mp:
            cumulative = ctx.mp_year_totals.get((mp.mp_id, fy), 0.0)
            # Raised only against works recommended past the line, not against
            # every work in a year that happened to end over it.
            if (
                cumulative > mp.annual_entitlement
                and work.work_id in ctx.entitlement_breach_works
            ):
                findings.append(
                    Finding(
                        code="ENTITLEMENT_EXCEEDED",
                        module=MODULE,
                        signal_value=round(cumulative, 2),
                        threshold_value=float(mp.annual_entitlement),
                        severity=SeverityTier.CRITICAL,
                        params={
                            "mp_name": mp.name,
                            "financial_year": _fy_label(fy),
                            "cumulative": rupees(cumulative),
                            "entitlement": rupees(mp.annual_entitlement),
                            "excess": rupees(cumulative - mp.annual_entitlement),
                        },
                    )
                )

            # --- 4. A Lok Sabha member recommends within their own constituency ---
            if mp.house == House.LOK_SABHA and mp.constituency != district.name:
                findings.append(
                    Finding(
                        code="OUT_OF_CONSTITUENCY",
                        module=MODULE,
                        signal_value=1.0,
                        threshold_value=0.0,
                        severity=SeverityTier.HIGH,
                        params={
                            "mp_name": mp.name,
                            "constituency": mp.constituency,
                            "district": district.name,
                        },
                    )
                )

        # --- 5. SC/ST area allocation, measured at district-year level ---
        # The shortfall belongs to the district's year, not to any one work. It
        # is raised against works in that year so it reaches a reviewer's queue,
        # and the sentence says plainly that it is a district-level finding.
        sc_st_value, total_value = ctx.district_quota.get((work.district_id, fy), (0.0, 0.0))
        # A shortfall belongs to the district's year. It is raised once, on a
        # single carrier work, rather than against every work in that year.
        if total_value > 0 and ctx.quota_carrier.get((work.district_id, fy)) == work.work_id:
            actual_pct = sc_st_value / total_value * 100
            required = ctx.config.t("SC_AREA_MIN_PCT")
            if actual_pct < required:
                shortfall = (required / 100 * total_value) - sc_st_value
                findings.append(
                    Finding(
                        code="QUOTA_SHORTFALL",
                        module=MODULE,
                        signal_value=round(actual_pct, 2),
                        threshold_value=required,
                        severity=SeverityTier.HIGH,
                        params={
                            "district": district.name,
                            "financial_year": _fy_label(fy),
                            "actual_pct": actual_pct,
                            "required_pct": required,
                            "quota_kind": "SC and ST",
                            "shortfall_amount": rupees(shortfall),
                            "total_amount": rupees(total_value),
                        },
                    )
                )

        # --- 6. A sanction decision within 45 days ---
        # Applies to a decision taken late as well as to one still outstanding.
        # Checking only pending works let a sanction granted 190 days late pass
        # in silence, which is the opposite of what the guideline is about.
        limit = ctx.config.t("SANCTION_DECISION_DAYS")
        if work.sanctioned_date is None:
            elapsed = (ctx.reference_date - work.recommended_date).days
            decided = False
        else:
            elapsed = (work.sanctioned_date - work.recommended_date).days
            decided = True

        if elapsed > limit:
            findings.append(
                Finding(
                    code="SANCTION_DELAY_45D",
                    module=MODULE,
                    signal_value=float(elapsed),
                    threshold_value=limit,
                    severity=SeverityTier.MEDIUM if elapsed < limit * 2 else SeverityTier.HIGH,
                    params={
                        "days_elapsed": elapsed,
                        "threshold": limit,
                        "decided": decided,
                    },
                )
            )

    # A rule either broke or it did not. The score reflects how many broke rather
    # than how badly, because there is no "how badly" for a deterministic rule.
    score = 0.0 if not findings else min(100.0, 60.0 + 20.0 * len(findings))
    return ModuleResult(MODULE, score, findings)
