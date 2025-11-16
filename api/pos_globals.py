"""
POS Global Configuration API

Exposes global POS application configuration from environment variables
available to the frontend.
"""

import os
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/globals", tags=["pos_globals"])


class POSGlobalsResponse(BaseModel):
    """POS global application configuration response."""
    frontend_project_name: str
    loyalty_points_rate: float


@router.get("", response_model=POSGlobalsResponse)
async def get_pos_globals() -> POSGlobalsResponse:
    """Get POS global application configuration from environment variables."""
    return POSGlobalsResponse(
        frontend_project_name=os.getenv("FRONTEND_PROJECT_NAME", "Agent Hub"),
        loyalty_points_rate=float(os.getenv("POS_LOYALTY_POINTS_RATE", "0.05"))
    )
