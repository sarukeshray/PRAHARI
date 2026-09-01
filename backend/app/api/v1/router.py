"""Aggregate router for /api/v1."""

from fastapi import APIRouter

from app.api.v1 import citizen, dashboards, lifecycle, system, works

api_router = APIRouter()
api_router.include_router(system.router)
api_router.include_router(works.router)
api_router.include_router(dashboards.router)
api_router.include_router(lifecycle.router)
api_router.include_router(citizen.router)
