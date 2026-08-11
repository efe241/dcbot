from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database import get_db
from backend.models.reward_item import RewardItem
from backend.services.reward_service import RewardService
from backend.api.auth import get_current_user_id
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rewards", tags=["Rewards"])

DEFAULT_REWARDS = [
    {
        "name": "50k OwO Cash (Min. Paket)",
        "description": "Discord sunucusunda 50,000 OwO parası ödülü (Minimum alım sınırı: 50 Coin).",
        "coin_price": Decimal("50.00"),
        "reward_type": "owo_cash",
        "icon_emoji": "🪙"
    },
    {
        "name": "200k OwO Cash",
        "description": "Discord sunucusunda 200,000 OwO parası ödülü (1 Coin = 1,000 OwO).",
        "coin_price": Decimal("200.00"),
        "reward_type": "owo_cash",
        "icon_emoji": "💰"
    },
    {
        "name": "500k OwO Cash",
        "description": "Discord sunucusunda 500,000 OwO parası ödülü (1 Coin = 1,000 OwO).",
        "coin_price": Decimal("500.00"),
        "reward_type": "owo_cash",
        "icon_emoji": "💎"
    },
    {
        "name": "1 Million OwO Cash",
        "description": "Discord sunucusunda 1,000,000 OwO parası büyük ödül (1 Coin = 1,000 OwO).",
        "coin_price": Decimal("1000.00"),
        "reward_type": "owo_cash",
        "icon_emoji": "👑"
    }
]

@router.get("/items")
async def get_reward_items(db: AsyncSession = Depends(get_db)):
    stmt = select(RewardItem).where(RewardItem.is_active == True)
    items = (await db.execute(stmt)).scalars().all()

    # Seed or refresh default items if 50k OwO Cash is missing
    has_50k = any("50k OwO" in (i.name or "") for i in items)
    if not items or not has_50k:
        for item in items:
            item.is_active = False
        await db.commit()
        for d in DEFAULT_REWARDS:
            item = RewardItem(**d)
            db.add(item)
        await db.commit()
        items = (await db.execute(stmt)).scalars().all()

    return [
        {
            "id": item.id,
            "name": item.name,
            "description": item.description,
            "coin_price": float(item.coin_price),
            "reward_type": item.reward_type,
            "duration_days": item.duration_days,
            "icon_emoji": item.icon_emoji
        }
        for item in items
    ]

@router.post("/purchase")
async def purchase_reward(
    payload: dict = Body(...),
    discord_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    item_id = payload.get("item_id")
    if not item_id:
        raise HTTPException(status_code=400, detail="item_id is required")

    success, message, item = await RewardService.purchase_reward_item(
        db, discord_id, int(item_id)
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {
        "status": "success",
        "message": message,
        "item": {
            "name": item.name,
            "reward_type": item.reward_type,
            "coin_price": float(item.coin_price)
        }
    }
