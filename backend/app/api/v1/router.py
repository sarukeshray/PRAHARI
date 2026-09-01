"""Aggregate router for /api/v1."""

from fastapi import APIRouter

from app.api.v1 import (
    agency,
    backtest,
    citizen,
    dashboards,
    lifecycle,
    reports,
    system,
    works,
)

api_router = APIRouter()
api_router.include_router(system.router)
api_router.include_router(works.router)
api_router.include_router(dashboards.router)
api_router.include_router(lifecycle.router)
api_router.include_router(citizen.router)
api_router.include_router(backtest.router)
api_router.include_router(agency.router)
api_router.include_router(reports.router)
