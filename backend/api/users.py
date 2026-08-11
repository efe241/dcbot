from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from backend.database import get_db
from backend.models.user import User
from backend.models.ledger import CoinLedger
from backend.models.transaction import CPXTransaction
from backend.api.auth import get_current_user_id
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/users", tags=["Users"])

@router.get("/me/history")
async def get_my_history(
    discord_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(CoinLedger).where(
        CoinLedger.discord_user_id == discord_id
    ).order_by(desc(CoinLedger.created_at)).limit(50)

    records = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": r.id,
            "amount": float(r.amount),
            "type": r.type,
            "reference_id": r.reference_id,
            "description": r.description,
            "created_at": r.created_at.isoformat() if r.created_at else None
        }
        for r in records
    ]

@router.get("/me/surveys")
async def get_my_surveys(
    discord_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(CPXTransaction).where(
        CPXTransaction.discord_user_id == discord_id
    ).order_by(desc(CPXTransaction.created_at)).limit(50)

    records = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": r.id,
            "trans_id": r.trans_id,
            "status": r.status,
            "amount_usd": float(r.amount_usd),
            "coin_amount": float(r.coin_amount),
            "created_at": r.created_at.isoformat() if r.created_at else None
        }
        for r in records
    ]

@router.get("/leaderboard")
async def get_leaderboard(db: AsyncSession = Depends(get_db)):
    stmt = select(User).order_by(desc(User.coin_balance)).limit(10)
    users = (await db.execute(stmt)).scalars().all()
    return [
        {
            "rank": idx + 1,
            "discord_username": u.discord_username,
            "discord_avatar": u.discord_avatar,
            "coin_balance": float(u.coin_balance)
        }
        for idx, u in enumerate(users)
    ]
