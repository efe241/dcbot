import pytest
import hashlib
from decimal import Decimal
from sqlalchemy import select
from backend.services.cpx_service import CPXService
from backend.services.reward_service import RewardService
from backend.models.user import User
from backend.models.transaction import CPXTransaction
from backend.models.ledger import CoinLedger
from backend.config import settings

@pytest.mark.asyncio
async def test_valid_completed_postback(db_session):
    """
    Test 1: Valid completed postback (Status = 1) -> Expects +1000 Coins credited.
    """
    trans_id = "TEST_TRANS_001"
    user_id = "111222333444555666"
    amount_usd = "1.0000"
    
    # Calculate valid hash
    valid_hash = CPXService.calculate_secure_hash(trans_id)

    params = {
        "trans_id": trans_id,
        "user_id": user_id,
        "status": 1,
        "amount_usd": amount_usd,
        "secure_hash": valid_hash,
        "ip_click": "1.2.3.4",
        "type": "survey"
    }

    success, msg, status_code = await RewardService.process_postback(db_session, params, "188.40.3.73")
    assert success is True
    assert status_code == 200

    # Verify user balance (1.00 USD * 100 = 100 Coins)
    stmt = select(User).where(User.discord_id == user_id)
    user = (await db_session.execute(stmt)).scalar_one()
    assert user.coin_balance == Decimal("100.00")

    # Verify ledger entry
    ledger_stmt = select(CoinLedger).where(CoinLedger.discord_user_id == user_id)
    ledger = (await db_session.execute(ledger_stmt)).scalar_one()
    assert ledger.amount == Decimal("100.00")
    assert ledger.type == "survey_reward"


@pytest.mark.asyncio
async def test_idempotency_duplicate_transaction(db_session):
    """
    Test 2: Same transaction processed twice -> Expects duplicate skipped, balance remains unchanged.
    """
    trans_id = "TEST_TRANS_DUP"
    user_id = "111222333444555666"
    valid_hash = CPXService.calculate_secure_hash(trans_id)

    params = {
        "trans_id": trans_id,
        "user_id": user_id,
        "status": 1,
        "amount_usd": "0.5000",
        "secure_hash": valid_hash
    }

    # 1st Call
    success1, msg1, code1 = await RewardService.process_postback(db_session, params, "188.40.3.73")
    assert success1 is True

    # 2nd Call (Duplicate)
    success2, msg2, code2 = await RewardService.process_postback(db_session, params, "188.40.3.73")
    assert success2 is True
    assert "Duplicate skipped" in msg2

    # Check user balance is only credited ONCE (50 coins)
    stmt = select(User).where(User.discord_id == user_id)
    user = (await db_session.execute(stmt)).scalar_one()
    assert user.coin_balance == Decimal("50.00")


@pytest.mark.asyncio
async def test_invalid_secure_hash(db_session):
    """
    Test 3: Invalid secure hash -> Expects rejection (403 Forbidden).
    """
    params = {
        "trans_id": "TEST_TRANS_HASH_ERR",
        "user_id": "111222333444555666",
        "status": 1,
        "amount_usd": "1.0000",
        "secure_hash": "invalid_fake_hash_12345"
    }

    success, msg, status_code = await RewardService.process_postback(db_session, params, "188.40.3.73")
    assert success is False
    assert status_code == 403
    assert "Invalid secure hash" in msg


@pytest.mark.asyncio
async def test_reversal_status_2(db_session):
    """
    Test 4: Status = 2 Reversal -> Expects coins deducted from user balance.
    """
    trans_id = "TEST_TRANS_REV"
    user_id = "111222333444555666"
    valid_hash = CPXService.calculate_secure_hash(trans_id)

    # Initial completion (+500 Coins)
    params_complete = {
        "trans_id": trans_id,
        "user_id": user_id,
        "status": 1,
        "amount_usd": "0.5000",
        "secure_hash": valid_hash
    }
    await RewardService.process_postback(db_session, params_complete, "188.40.3.73")

    # Reversal (-500 Coins)
    params_reverse = {
        "trans_id": trans_id,
        "user_id": user_id,
        "status": 2,
        "amount_usd": "0.5000",
        "secure_hash": valid_hash
    }
    success, msg, status_code = await RewardService.process_postback(db_session, params_reverse, "188.40.3.73")
    assert success is True
    assert status_code == 200

    # User balance should return to 0
    stmt = select(User).where(User.discord_id == user_id)
    user = (await db_session.execute(stmt)).scalar_one()
    assert user.coin_balance == Decimal("0.00")


@pytest.mark.asyncio
async def test_unauthorized_ip(db_session):
    """
    Test 6: Postback from non-whitelisted IP -> Expects rejection (403).
    """
    trans_id = "TEST_TRANS_IP"
    valid_hash = CPXService.calculate_secure_hash(trans_id)

    params = {
        "trans_id": trans_id,
        "user_id": "111222333",
        "status": 1,
        "amount_usd": "1.0000",
        "secure_hash": valid_hash
    }

    # Temporarily set environment to production to enforce IP check strictly
    original_env = settings.ENVIRONMENT
    settings.ENVIRONMENT = "production"

    try:
        success, msg, status_code = await RewardService.process_postback(db_session, params, "99.99.99.99")
        assert success is False
        assert status_code == 403
        assert "Unauthorized IP" in msg
    finally:
        settings.ENVIRONMENT = original_env


@pytest.mark.asyncio
async def test_negative_amount_rejection(db_session):
    """
    Test 7: Negative amount completion -> Expects rejection (400).
    """
    trans_id = "TEST_TRANS_NEG"
    valid_hash = CPXService.calculate_secure_hash(trans_id)

    params = {
        "trans_id": trans_id,
        "user_id": "111222333",
        "status": 1,
        "amount_usd": "-5.0000",
        "secure_hash": valid_hash
    }

    success, msg, status_code = await RewardService.process_postback(db_session, params, "188.40.3.73")
    assert success is False
    assert status_code == 400
    assert "Invalid negative amount" in msg
