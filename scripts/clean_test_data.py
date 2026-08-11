import asyncio
import os
import sys
from decimal import Decimal

# Add current dir to sys.path
sys.path.insert(0, os.path.abspath("."))

from backend.database import AsyncSessionLocal
from backend.models.user import User
from backend.models.transaction import CPXTransaction
from backend.models.ledger import CoinLedger
from backend.models.log import PostbackLog
from sqlalchemy import select, delete

TEST_USER_IDS = [
    "123456789012345678",
    "987654321098765432",
    "user-abc-789",
    "999888777"
]

async def clean_database():
    print("[+] Cleaning test users and test transactions from Database...")
    async with AsyncSessionLocal() as db:
        # 1. Delete test users
        for uid in TEST_USER_IDS:
            await db.execute(delete(User).where(User.discord_id == uid))
            await db.execute(delete(CoinLedger).where(CoinLedger.discord_user_id == uid))
            await db.execute(delete(CPXTransaction).where(CPXTransaction.discord_user_id == uid))
            await db.execute(delete(PostbackLog).where(PostbackLog.user_id == uid))

        # 2. Delete test transactions (amount >= 50 USD or trans_id with test/TEST/txn-)
        stmt_test_tx = select(CPXTransaction).where(
            (CPXTransaction.amount_usd >= Decimal("50.00")) |
            (CPXTransaction.trans_id.ilike("%test%")) |
            (CPXTransaction.trans_id.ilike("%txn-%"))
        )
        test_txs = (await db.execute(stmt_test_tx)).scalars().all()
        for tx in test_txs:
            await db.execute(delete(CoinLedger).where(CoinLedger.reference_id == tx.trans_id))
            await db.execute(delete(CPXTransaction).where(CPXTransaction.id == tx.id))

        # 3. Delete invalid test postback logs
        await db.execute(delete(PostbackLog).where(
            (PostbackLog.raw_params.ilike("%test%")) |
            (PostbackLog.raw_params.ilike("%500%")) |
            (PostbackLog.user_id.in_(TEST_USER_IDS))
        ))

        # 4. Recalculate real user balances based on remaining CoinLedger
        users = (await db.execute(select(User))).scalars().all()
        for u in users:
            ledger_entries = (await db.execute(
                select(CoinLedger).where(CoinLedger.discord_user_id == u.discord_id)
            )).scalars().all()
            total_bal = sum(l.amount for l in ledger_entries if l.amount is not None)
            if total_bal < 0:
                total_bal = Decimal("0.00")
            u.coin_balance = Decimal(str(total_bal))

        await db.commit()
        print("[+] Database cleanup finished successfully!")

if __name__ == "__main__":
    asyncio.run(clean_database())
