"""Audit-ready PDF export.

Generated server-side from the same queries the screens read, so the document a
reviewer files cannot disagree with the dashboard they were looking at. Building
it in the browser would mean re-deriving the figures somewhere else, which is how
a report and a screen drift apart.

Every page carries the synthetic-data notice. A printed page outlives the browser
tab it came from, and a table of rupee figures with no provenance is exactly the
thing that gets mistaken for a real record.
"""

from __future__ import annotations

import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, Scope, require_roles, scope
from app.db import get_db
from app.models import District, Work
from app.models.enums import FlagStatus, Role, SeverityTier
from app.models.risk import RiskAssessment, RiskFlag

router = APIRouter()

NOTICE = "SYNTHETIC DEMONSTRATION DATA - NOT LIVE MPLADS RECORDS"


def _footer(canvas, doc):
    """The provenance notice, on every page, in the margin."""
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColorRGB(0.42, 0.40, 0.07)
    canvas.drawString(36, 24, NOTICE)
    canvas.setFillColorRGB(0.55, 0.58, 0.61)
    canvas.drawRightString(559, 24, f"Page {doc.page}")
    canvas.restoreState()


@router.get("/reports/district/{district_id}.pdf", tags=["reports"])
def district_report(
    district_id: str,
    db: Session = Depends(get_db),
    sc: Scope = Depends(scope),
    user: CurrentUser = Depends(
        require_roles(Role.DISTRICT_AUTHORITY, Role.STATE_NODAL, Role.MINISTRY)
    ),
    severity: SeverityTier | None = Query(default=None),
) -> StreamingResponse:
    """A district's open findings, as a filed document."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        BaseDocTemplate,
        Frame,
        PageTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )

    district = db.get(District, district_id)
    visible = sc.works(select(Work.work_id).where(Work.district_id == district_id))

    stmt = (
        select(RiskFlag, Work)
        .join(Work, Work.work_id == RiskFlag.work_id)
        .where(RiskFlag.work_id.in_(visible), RiskFlag.status == FlagStatus.OPEN)
    )
    if severity:
        stmt = stmt.where(RiskFlag.severity_tier == severity)

    rank = {SeverityTier.CRITICAL: 0, SeverityTier.HIGH: 1, SeverityTier.MEDIUM: 2, SeverityTier.LOW: 3}
    rows = sorted(db.execute(stmt).all(), key=lambda r: rank[r[0].severity_tier])

    total_works = db.scalar(select(func.count()).select_from(visible.subquery())) or 0
    screened = db.scalar(
        select(func.count(func.distinct(RiskAssessment.work_id))).where(
            RiskAssessment.work_id.in_(visible)
        )
    ) or 0

    buffer = io.BytesIO()
    doc = BaseDocTemplate(
        buffer, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title=f"PRAHARI findings — {district.name if district else district_id}",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="body")
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=_footer)])

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=15, spaceAfter=2, textColor=colors.HexColor("#14181b"))
    meta = ParagraphStyle("meta", parent=styles["Normal"], fontSize=8.5, textColor=colors.HexColor("#5b656e"))
    body = ParagraphStyle("body", parent=styles["Normal"], fontSize=8, leading=10)
    note = ParagraphStyle("note", parent=styles["Normal"], fontSize=8, leading=11, textColor=colors.HexColor("#6b5312"))

    story = [
        Paragraph(f"Open findings — {district.name if district else district_id}", h1),
        Paragraph(
            f"{district.state if district else ''} · generated "
            f"{datetime.utcnow():%d %b %Y %H:%M} UTC · by {user.display_name}",
            meta,
        ),
        Spacer(1, 5 * mm),
        Paragraph(
            "<b>This document contains synthetic demonstration data.</b> Every finding below is "
            "a risk indicator requiring human investigation, not a determination of wrongdoing. "
            "No figure here reflects a live MPLADS record.",
            note,
        ),
        Spacer(1, 5 * mm),
        Paragraph(
            f"{len(rows)} open findings across {screened} of {total_works} screened works.", meta
        ),
        Spacer(1, 4 * mm),
    ]

    table_data = [["Work", "Tier", "Finding", "Observed", "Threshold"]]
    for flag, work in rows[:400]:
        table_data.append(
            [
                Paragraph(f"<b>{work.work_id}</b><br/>{work.work_type}<br/>{work.block}", body),
                flag.severity_tier.value,
                Paragraph(f"<b>{flag.flag_code}</b><br/>{flag.explanation}", body),
                f"{flag.signal_value:,.2f}",
                f"{flag.threshold_value:,.2f}",
            ]
        )

    if len(table_data) == 1:
        story.append(Paragraph("No open findings match this filter.", body))
    else:
        table = Table(
            table_data,
            colWidths=[26 * mm, 15 * mm, 92 * mm, 20 * mm, 20 * mm],
            repeatRows=1,
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f4f5f6")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#5b656e")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dce0e2")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(table)

    if len(rows) > 400:
        story.append(Spacer(1, 4 * mm))
        story.append(
            Paragraph(f"Truncated at 400 findings; {len(rows)} are open in total.", meta)
        )

    doc.build(story)
    buffer.seek(0)

    filename = f"prahari-{district_id}-{datetime.utcnow():%Y%m%d}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
