from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from backend.database import get_db
from backend.models.user import User
from backend.models.transaction import CPXTransaction
from backend.models.ledger import CoinLedger
from backend.models.log import PostbackLog
from backend.services.reward_service import RewardService
from backend.api.auth import get_current_user_id
from backend.config import settings
from decimal import Decimal
import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["Admin"])

async def verify_admin(discord_id: str = Depends(get_current_user_id)):
    if discord_id in settings.admin_ids_list or settings.ENVIRONMENT == "development":
        return discord_id
    raise HTTPException(status_code=403, detail="Admin privilege required")

@router.get("/stats")
async def get_admin_stats(
    admin_id: str = Depends(verify_admin),
    db: AsyncSession = Depends(get_db)
):
    # Total Users
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0

    # Active Users (completed at least 1 survey or logged in)
    active_users = (await db.execute(
        select(func.count(func.distinct(CPXTransaction.discord_user_id))).where(CPXTransaction.status == 1)
    )).scalar() or 0

    # Completed Surveys (status = 1)
    completed_surveys = (await db.execute(
        select(func.count(CPXTransaction.id)).where(CPXTransaction.status == 1)
    )).scalar() or 0

    # Reversals (status = 2)
    reversals_count = (await db.execute(
        select(func.count(CPXTransaction.id)).where(CPXTransaction.status == 2)
    )).scalar() or 0

    # Fraud / Flagged logs
    fraud_logs_count = (await db.execute(
        select(func.count(PostbackLog.id)).where(PostbackLog.hash_valid == False)
    )).scalar() or 0

    # Total CPX Revenue USD (from status = 1 minus status = 2)
    revenue_credited = (await db.execute(
        select(func.sum(CPXTransaction.amount_usd)).where(CPXTransaction.status == 1)
    )).scalar() or Decimal("0.00")

    revenue_reversed = (await db.execute(
        select(func.sum(CPXTransaction.amount_usd)).where(CPXTransaction.status == 2)
    )).scalar() or Decimal("0.00")

    total_revenue_usd = max(Decimal("0.00"), revenue_credited - revenue_reversed)

    # Coins Distributed
    coins_distributed = (await db.execute(
        select(func.sum(CoinLedger.amount)).where(CoinLedger.amount > 0)
    )).scalar() or Decimal("0.00")

    # Coins Spent
    coins_spent = (await db.execute(
        select(func.sum(-CoinLedger.amount)).where(CoinLedger.type == "shop_purchase")
    )).scalar() or Decimal("0.00")

    # Calculated metrics
    rev_per_user = float(total_revenue_usd / active_users) if active_users > 0 else 0.0
    rev_per_survey = float(total_revenue_usd / completed_surveys) if completed_surveys > 0 else 0.0
    completion_rate = float((completed_surveys / (completed_surveys + reversals_count)) * 100) if (completed_surveys + reversals_count) > 0 else 100.0

    return {
        "total_users": total_users,
        "active_users": active_users,
        "completed_surveys": completed_surveys,
        "reversals_count": reversals_count,
        "fraud_logs_count": fraud_logs_count,
        "total_revenue_usd": float(total_revenue_usd),
        "coins_distributed": float(coins_distributed),
        "coins_spent": float(coins_spent),
        "revenue_per_user": round(rev_per_user, 4),
        "revenue_per_survey": round(rev_per_survey, 4),
        "completion_rate_pct": round(completion_rate, 2)
    }

@router.get("/users")
async def get_users_list(
    admin_id: str = Depends(verify_admin),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(User).order_by(desc(User.created_at)).limit(100)
    users = (await db.execute(stmt)).scalars().all()

    return [
        {
            "id": u.id,
            "discord_id": u.discord_id,
            "discord_username": u.discord_username,
            "coin_balance": float(u.coin_balance),
            "is_banned": u.is_banned,
            "risk_score": u.risk_score,
            "created_at": u.created_at.isoformat() if u.created_at else None
        }
        for u in users
    ]

@router.get("/postback-logs")
async def get_postback_logs(
    admin_id: str = Depends(verify_admin),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(PostbackLog).order_by(desc(PostbackLog.created_at)).limit(100)
    logs = (await db.execute(stmt)).scalars().all()

    return [
        {
            "id": l.id,
            "ip_address": l.ip_address,
            "trans_id": l.trans_id,
            "user_id": l.user_id,
            "status": l.status,
            "amount_usd": float(l.amount_usd) if l.amount_usd else 0.0,
            "hash_valid": l.hash_valid,
            "ip_whitelisted": l.ip_whitelisted,
            "processed": l.processed,
            "error_message": l.error_message,
            "created_at": l.created_at.isoformat() if l.created_at else None
        }
        for l in logs
    ]

@router.post("/adjust-coins")
async def adjust_coins(
    payload: dict = Body(...),
    admin_id: str = Depends(verify_admin),
    db: AsyncSession = Depends(get_db)
):
    target_user_id = str(payload.get("discord_id", "")).strip()
    amount_val = payload.get("amount", 0)
    action = payload.get("action", "add")  # "add" or "remove"
    reason = payload.get("reason", "Admin manual adjustment")

    if not target_user_id:
        raise HTTPException(status_code=400, detail="target_user_id is required")

    try:
        amount = Decimal(str(amount_val))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid numeric amount")

    is_addition = (action == "add")
    success, message, new_bal = await RewardService.admin_adjust_coins(
        db, target_user_id, amount, is_addition, admin_id, reason
    )

    return {
        "status": "success",
        "message": message,
        "new_balance": float(new_bal)
    }
