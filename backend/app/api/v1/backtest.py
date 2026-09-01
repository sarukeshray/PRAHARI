"""Backtest endpoints.

Replaying the cases builds an isolated scratch database and scores it, which
takes a few seconds. It is therefore a POST, not a GET: it is a computation the
caller asks for, not a resource they read.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, current_user
from app.backtest import cag_cases
from app.backtest.sensitivity import compute_sensitivity
from app.db import get_db

router = APIRouter()


@router.get("/backtest/cases", tags=["backtest"])
def list_cases(user: CurrentUser = Depends(current_user)) -> list[dict]:
    """The documented findings each case reconstructs, and its source."""
    return cag_cases.list_cases()


@router.post("/backtest/run", tags=["backtest"])
def run(user: CurrentUser = Depends(current_user)) -> dict:
    """Build every case in a scratch database, score it, and report what fired."""
    return cag_cases.run_backtest()


@router.get("/backtest/sensitivity", tags=["backtest"])
def sensitivity(
    db: Session = Depends(get_db), user: CurrentUser = Depends(current_user)
) -> dict:
    """Recall against the planted answer key, computed from the live corpus."""
    return compute_sensitivity(db)
