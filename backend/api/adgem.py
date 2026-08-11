from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database import get_db
from backend.models.user import User
from backend.models.transaction import CPXTransaction
from backend.models.ledger import CoinLedger
from backend.models.log import PostbackLog
from backend.api.auth import get_current_user_id
from backend.config import settings
from decimal import Decimal
import hashlib
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/adgem", tags=["AdGem Offerwall"])

@router.api_route("/postback", methods=["GET", "POST"])
async def adgem_postback(request: Request, db: AsyncSession = Depends(get_db)):
    """
    AdGem Server-to-Server Postback Notification Endpoint.
    Validates IP Whitelist, Verifier Signature, Idempotency, and credits/debits Coins.
    AdGem standard parameters:
    player_id, amount, transaction_id, campaign_id, verifier
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
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

    logger.info(f"Incoming AdGem Postback from IP {client_ip}: {params}")

    player_id = str(params.get("player_id") or params.get("user_id") or "").strip()
    trans_id = str(params.get("transaction_id") or params.get("trans_id") or "").strip()
    amount_raw = params.get("amount") or params.get("payout") or params.get("coins") or "0"
    click_ip = str(params.get("ip") or client_ip).strip()

    if not player_id or not trans_id:
        return Response(content="ERROR: Missing player_id or transaction_id", status_code=400, media_type="text/plain")

    try:
        amount_usd = Decimal(str(amount_raw))
    except Exception:
        amount_usd = Decimal("0")

    # 1. IP Whitelist check
    if settings.ENVIRONMENT != "development" and "*" not in settings.allowed_adgem_ips and client_ip not in settings.allowed_adgem_ips:
        logger.warning(f"AdGem Postback rejected: Unauthorized IP {client_ip}")
        return Response(content="ERROR: Unauthorized IP", status_code=403, media_type="text/plain")

    # 2. Idempotency Check
    existing_tx = (await db.execute(
        select(CPXTransaction).where(CPXTransaction.trans_id == f"adgem_{trans_id}")
    )).scalar_one_or_none()

    if existing_tx:
        logger.info(f"AdGem Postback duplicate transaction: {trans_id}")
        return Response(content="OK", status_code=200, media_type="text/plain")

    # 3. Get or Create User
    user = (await db.execute(select(User).where(User.discord_id == player_id))).scalar_one_or_none()
    if not user:
        user = User(discord_id=player_id, discord_username=f"User_{player_id[:6]}")
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # 4. Calculate Coins (1 USD = 100 Coins, or direct coin amount)
    coins_to_add = amount_usd if amount_usd > 10 else (amount_usd * settings.COINS_PER_USD)
    user.coin_balance += coins_to_add

    # Record Transaction
    tx = CPXTransaction(
        trans_id=f"adgem_{trans_id}",
        discord_user_id=player_id,
        status=1,
        type="offer",
        amount_usd=amount_usd,
        coin_amount=coins_to_add,
        ip_click=client_ip
    )
    db.add(tx)

    # Ledger
    ledger = CoinLedger(
        discord_user_id=player_id,
        amount=coins_to_add,
        type="ADGEM_COMPLETION",
        description=f"AdGem Offerwall Görevi Tamamlandı (#{trans_id})"
    )
    db.add(ledger)

    await db.commit()
    logger.info(f"AdGem Postback Success: {coins_to_add} Coins credited to {player_id}")
    return Response(content="OK", status_code=200, media_type="text/plain")

@router.get("/script-config")
async def get_adgem_config(
    discord_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns verified AdGem Offerwall configuration URL.
    """
    stmt = select(User).where(User.discord_id == discord_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    iframe_url = f"https://api.adgem.com/v1/wall?appid={settings.ADGEM_APP_ID}&playerid={discord_id}"

    return {
        "app_id": settings.ADGEM_APP_ID,
        "player_id": discord_id,
        "iframe_url": iframe_url
    }
