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
        "name": "1x Giveaway Ticket",
        "description": "Discord sunucusundaki özel çekilişlere katılım bileti.",
        "coin_price": Decimal("500.00"),
        "reward_type": "giveaway_ticket",
        "icon_emoji": "🎟️"
    },
    {
        "name": "7 Günlük VIP Rolü",
        "description": "Sunucuda 7 gün boyunca VIP rolü ve özel kanal erişimi.",
        "coin_price": Decimal("2500.00"),
        "reward_type": "vip",
        "duration_days": 7,
        "icon_emoji": "⭐"
    },
    {
        "name": "30 Günlük VIP Rolü",
        "description": "Sunucuda 30 gün boyunca VIP rolü, XP boost ve özel yetkiler.",
        "coin_price": Decimal("7500.00"),
        "reward_type": "vip",
        "duration_days": 30,
        "icon_emoji": "👑"
    },
    {
        "name": "Özel Discord Rolü",
        "description": "İstediğin renkte ve isimde özel Discord rolü hakkı.",
        "coin_price": Decimal("15000.00"),
        "reward_type": "custom",
        "icon_emoji": "🎨"
    }
]

@router.get("/items")
async def get_reward_items(db: AsyncSession = Depends(get_db)):
    stmt = select(RewardItem).where(RewardItem.is_active == True)
    items = (await db.execute(stmt)).scalars().all()

    # Seed default items if empty
    if not items:
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
