import pytest
from decimal import Decimal
from backend.services.reward_service import RewardService
from backend.models.user import User
from backend.models.reward_item import RewardItem
from backend.models.ledger import CoinLedger
from sqlalchemy import select

@pytest.mark.asyncio
async def test_admin_adjust_coins(db_session):
    user_id = "999888777666"
    admin_id = "111111111111"

    # Add 5000 Coins
    success, msg, new_bal = await RewardService.admin_adjust_coins(
        db_session, user_id, Decimal("5000.00"), True, admin_id, "Test credit"
    )
    assert success is True
    assert new_bal == Decimal("5000.00")

    # Remove 1500 Coins
    success, msg, new_bal2 = await RewardService.admin_adjust_coins(
        db_session, user_id, Decimal("1500.00"), False, admin_id, "Test debit"
    )
    assert success is True
    assert new_bal2 == Decimal("3500.00")


@pytest.mark.asyncio
async def test_purchase_reward_item(db_session):
    user_id = "999888777666"
    admin_id = "111111111111"

    # Create reward item
    item = RewardItem(
        name="VIP Role",
        description="7 days VIP access",
        coin_price=Decimal("2000.00"),
        reward_type="vip",
        icon_emoji="⭐"
    )
    db_session.add(item)
    await db_session.commit()

    # Credit user 5000 coins
    await RewardService.admin_adjust_coins(
        db_session, user_id, Decimal("5000.00"), True, admin_id, "Initial balance"
    )

    # Purchase item (cost: 2000 coins)
    success, msg, purchased_item = await RewardService.purchase_reward_item(
        db_session, user_id, item.id
    )
    assert success is True
    assert purchased_item.name == "VIP Role"

    # Verify updated balance (5000 - 2000 = 3000)
    user_stmt = select(User).where(User.discord_id == user_id)
    user = (await db_session.execute(user_stmt)).scalar_one()
    assert user.coin_balance == Decimal("3000.00")


@pytest.mark.asyncio
async def test_insufficient_balance_purchase(db_session):
    user_id = "poor_user_123"

    item = RewardItem(
        name="Expensive Custom Role",
        coin_price=Decimal("10000.00"),
        reward_type="custom",
        icon_emoji="👑"
    )
    db_session.add(item)
    await db_session.commit()

    # Try purchase with 0 balance
    success, msg, item = await RewardService.purchase_reward_item(
        db_session, user_id, item.id
    )
    assert success is False
    assert "Insufficient balance" in msg
