"""PRAHARI — AI-assisted preventive oversight for the MPLAD Scheme.

All records served by this API are synthetic.  No output of this system is a
determination of wrongdoing; every flag is a risk indicator routed to a human
reviewer, who makes the decision.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config.settings import settings

app = FastAPI(
    title="PRAHARI API",
    version=settings.engine_version,
    description=(
        "Preventive oversight screening for MPLADS works. "
        "Outputs are risk indicators requiring human review, not determinations."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
