from decimal import Decimal
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from backend.models.transaction import CPXTransaction
from backend.models.user import User
import datetime
import logging

logger = logging.getLogger(__name__)

class FraudService:
    @staticmethod
    async def evaluate_transaction_risk(
        db: AsyncSession,
        user_id: str,
        amount_usd: Decimal,
        ip_click: str,
        hash_valid: bool,
        ip_whitelisted: bool
    ) -> int:
        score = 0

        # Critical penalty for invalid secure hash
        if not hash_valid:
            score += 60

        # Penalty for non-whitelisted IP
        if not ip_whitelisted:
            score += 40

        # Anormal high amount flag (> $10.00 USD for single survey)
        if amount_usd > Decimal("10.00"):
            score += 35
        elif amount_usd > Decimal("5.00"):
            score += 20

        # Negative amount flag
        if amount_usd < Decimal("0.00"):
            score += 100

        # Check rapid completion velocity (e.g. > 3 surveys in last 2 minutes)
        two_mins_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=2)
        stmt = select(func.count(CPXTransaction.id)).where(
            CPXTransaction.discord_user_id == user_id,
            CPXTransaction.created_at >= two_mins_ago
        )
        recent_count = (await db.execute(stmt)).scalar() or 0
        if recent_count >= 3:
            score += 30

        # Check IP sharing (multiple discord users from same click IP)
        if ip_click:
            ip_stmt = select(func.count(func.distinct(CPXTransaction.discord_user_id))).where(
                CPXTransaction.ip_click == ip_click
            )
            distinct_users = (await db.execute(ip_stmt)).scalar() or 0
            if distinct_users >= 4:
                score += 25

        final_score = min(100, max(0, score))
        logger.info(f"Risk evaluation for user {user_id}: score={final_score}")
        return final_score

    @staticmethod
    def get_risk_level(score: int) -> str:
        if score <= 30:
            return "normal"
        elif score <= 60:
            return "review"
        elif score <= 80:
            return "delay"
        else:
            return "admin_flagged"
