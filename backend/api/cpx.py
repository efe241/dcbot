from fastapi import APIRouter, Depends, HTTPException, Request, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database import get_db
from backend.models.user import User
from backend.services.cpx_service import CPXService
from backend.services.reward_service import RewardService
from backend.api.auth import get_current_user_id
from backend.config import settings
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/cpx", tags=["CPX Research"])

@router.api_route("/postback", methods=["GET", "POST"])
async def cpx_postback(request: Request, db: AsyncSession = Depends(get_db)):
    """
    CPX Server-to-Server Postback Notification Endpoint.
    Validates IP Whitelist, Secure Hash, Idempotency, Status, Amount and credits/debits Coins.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"

    # Forwarded IP header support (e.g. Nginx proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()

    if request.method == "POST":
        try:
            params = await request.json()
        except Exception:
            params = dict(request.query_params)
    else:
        params = dict(request.query_params)

    logger.info(f"Incoming CPX Postback from IP {client_ip}: {params}")

    success, message, http_status = await RewardService.process_postback(db, params, client_ip)

    if not success:
        return Response(content=f"ERROR: {message}", status_code=http_status, media_type="text/plain")

    return Response(content="OK", status_code=http_status, media_type="text/plain")

@router.get("/script-config")
async def get_script_config(
    discord_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Generates verified CPX SurveyWall config script parameters.
    The secure_hash is safely computed on server side.
    """
    stmt = select(User).where(User.discord_id == discord_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    secure_hash = CPXService.calculate_user_secure_hash(discord_id)

    return {
        "app_id": settings.CPX_APP_ID,
        "ext_user_id": discord_id,
        "secure_hash": secure_hash,
        "username": user.discord_username,
        "email": user.email or "",
        "coins_per_usd": float(settings.COINS_PER_USD),
        "user_balance": float(user.coin_balance)
    }
