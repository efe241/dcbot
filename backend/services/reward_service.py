from decimal import Decimal
from typing import Dict, Any, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.exc import IntegrityError
from backend.models.user import User
from backend.models.transaction import CPXTransaction
from backend.models.ledger import CoinLedger
from backend.models.reward_item import RewardItem
from backend.models.log import PostbackLog
from backend.services.cpx_service import CPXService
from backend.services.fraud_service import FraudService
from backend.config import settings
import logging
import json

logger = logging.getLogger(__name__)

class RewardService:
    @staticmethod
    async def process_postback(
        db: AsyncSession,
        params: Dict[str, Any],
        client_ip: str
    ) -> Tuple[bool, str, int]:
        """
        Process CPX server postback atomically.
        Returns: (success: bool, message: str, http_status_code: int)
        """
        raw_params_str = json.dumps(params)
        trans_id = str(params.get("trans_id") or "").strip()
        user_id = str(params.get("user_id") or "").strip()
        status_val = params.get("status")
        
        try:
            status = int(status_val) if status_val is not None else 1
        except ValueError:
            status = 1

        try:
            amount_usd = Decimal(str(params.get("amount_usd") or "0.0000"))
        except Exception:
            amount_usd = Decimal("0.0000")

        received_hash = str(params.get("secure_hash") or "").strip()
        ip_click = str(params.get("ip_click") or "").strip()
        subid_1 = str(params.get("subid_1") or "").strip()
        subid_2 = str(params.get("subid_2") or "").strip()
        trans_type = str(params.get("type") or "survey").strip()

        # Step 1: Validate IP Whitelist
        ip_whitelisted = CPXService.is_ip_whitelisted(client_ip)
        
        # Step 2: Validate Secure Hash
        hash_valid = CPXService.verify_postback_hash(trans_id, received_hash)

        # Log incoming postback
        log_entry = PostbackLog(
            ip_address=client_ip,
            trans_id=trans_id,
            user_id=user_id,
            status=status,
            amount_usd=amount_usd,
            hash_valid=hash_valid,
            ip_whitelisted=ip_whitelisted,
            raw_params=raw_params_str
        )
        db.add(log_entry)

        # Basic validations before processing
        if not trans_id:
            log_entry.error_message = "Missing trans_id"
            await db.commit()
            return False, "Missing trans_id", 400

        if not user_id:
            log_entry.error_message = "Missing user_id"
            await db.commit()
            return False, "Missing user_id", 400

        if not hash_valid:
            log_entry.error_message = "Invalid secure hash"
            await db.commit()
            return False, "Invalid secure hash", 403

        if not ip_whitelisted:
            log_entry.error_message = f"IP {client_ip} is not whitelisted"
            await db.commit()
            return False, "Unauthorized IP address", 403

        if amount_usd < Decimal("0.0000") and status == 1:
            log_entry.error_message = "Invalid negative amount"
            await db.commit()
            return False, "Invalid negative amount", 400

        # Evaluate risk score
        risk_score = await FraudService.evaluate_transaction_risk(
            db, user_id, amount_usd, ip_click, hash_valid, ip_whitelisted
        )

        # Calculate Coin reward
        coin_amount = amount_usd * settings.COINS_PER_USD

        # Check existing transaction for Idempotency
        existing_tx_stmt = select(CPXTransaction).where(CPXTransaction.trans_id == trans_id)
        existing_tx = (await db.execute(existing_tx_stmt)).scalar_one_or_none()

        # Step 3: Handle Status = 1 (Completion / Credit)
        if status == 1:
            if existing_tx:
                if existing_tx.status == 1:
                    log_entry.processed = True
                    log_entry.error_message = "Duplicate transaction already processed"
                    await db.commit()
                    return True, "OK (Duplicate skipped)", 200
                elif existing_tx.status == 2:
                    log_entry.error_message = "Cannot re-credit a reversed transaction"
                    await db.commit()
                    return False, "Transaction was previously reversed", 400

            # Find or create User
            user_stmt = select(User).where(User.discord_id == user_id)
            user = (await db.execute(user_stmt)).scalar_one_or_none()
            if not user:
                user = User(
                    discord_id=user_id,
                    discord_username=f"User_{user_id[:6]}",
                    coin_balance=Decimal("0.00")
                )
                db.add(user)
                await db.flush()

            # Credit Coins
            user.coin_balance += coin_amount

            # Insert Ledger record
            ledger_entry = CoinLedger(
                discord_user_id=user_id,
                amount=coin_amount,
                type="survey_reward",
                reference_id=trans_id,
                description=f"CPX Survey Reward (${amount_usd:.2f} USD)"
            )
            db.add(ledger_entry)

            # Insert CPXTransaction record
            tx_record = CPXTransaction(
                trans_id=trans_id,
                discord_user_id=user_id,
                status=1,
                type=trans_type,
                amount_usd=amount_usd,
                coin_amount=coin_amount,
                ip_click=ip_click,
                subid_1=subid_1,
                subid_2=subid_2,
                secure_hash_valid=hash_valid,
                risk_score=risk_score
            )
            db.add(tx_record)

            log_entry.processed = True
            await db.commit()
            logger.info(f"Successfully credited {coin_amount} Coins to {user_id} for trans_id {trans_id}")
            return True, "OK", 200

        # Step 4: Handle Status = 2 (Reversal / Fraud Chargeback)
        elif status == 2:
            if existing_tx and existing_tx.status == 2:
                log_entry.processed = True
                log_entry.error_message = "Duplicate reversal already processed"
                await db.commit()
                return True, "OK (Duplicate reversal skipped)", 200

            user_stmt = select(User).where(User.discord_id == user_id)
            user = (await db.execute(user_stmt)).scalar_one_or_none()

            # Deduct coins if user exists
            if user:
                user.coin_balance -= coin_amount

            # Insert Reversal Ledger
            ledger_entry = CoinLedger(
                discord_user_id=user_id,
                amount=-coin_amount,
                type="survey_reversal",
                reference_id=trans_id,
                description=f"CPX Survey Reversal/Fraud (-${amount_usd:.2f} USD)"
            )
            db.add(ledger_entry)

            if existing_tx:
                existing_tx.status = 2
                existing_tx.updated_at = func.now()
            else:
                tx_record = CPXTransaction(
                    trans_id=trans_id,
                    discord_user_id=user_id,
                    status=2,
                    type=trans_type,
                    amount_usd=amount_usd,
                    coin_amount=coin_amount,
                    ip_click=ip_click,
                    subid_1=subid_1,
                    subid_2=subid_2,
                    secure_hash_valid=hash_valid,
                    risk_score=risk_score
                )
                db.add(tx_record)

            log_entry.processed = True
            await db.commit()
            logger.warning(f"Reversed {coin_amount} Coins for user {user_id} on trans_id {trans_id}")
            return True, "OK (Reversal processed)", 200

        else:
            log_entry.error_message = f"Unknown status code {status}"
            await db.commit()
            return False, f"Unknown status {status}", 400

    @staticmethod
    async def admin_adjust_coins(
        db: AsyncSession,
        discord_user_id: str,
        amount: Decimal,
        is_addition: bool,
        admin_discord_id: str,
        reason: str = "Admin adjustment"
    ) -> Tuple[bool, str, Decimal]:
        """
        Manually add or remove coins from user account with ledger logging.
        """
        user_stmt = select(User).where(User.discord_id == discord_user_id)
        user = (await db.execute(user_stmt)).scalar_one_or_none()

        if not user:
            user = User(
                discord_id=discord_user_id,
                discord_username=f"User_{discord_user_id[:6]}",
                coin_balance=Decimal("0.00")
            )
            db.add(user)
            await db.flush()

        adjusted_amount = amount if is_addition else -amount
        action_type = "admin_reward" if is_addition else "admin_deduction"

        user.coin_balance += adjusted_amount

        ledger_entry = CoinLedger(
            discord_user_id=discord_user_id,
            amount=adjusted_amount,
            type=action_type,
            reference_id=f"admin_{admin_discord_id}",
            description=f"{reason} (By admin {admin_discord_id})"
        )
        db.add(ledger_entry)
        await db.commit()

        return True, "Balance updated", user.coin_balance

    @staticmethod
    async def purchase_reward_item(
        db: AsyncSession,
        discord_user_id: str,
        item_id: int
    ) -> Tuple[bool, str, Optional[RewardItem]]:
        """
        Purchase a digital reward item using virtual coins.
        """
        user_stmt = select(User).where(User.discord_id == discord_user_id)
        user = (await db.execute(user_stmt)).scalar_one_or_none()

        if not user:
            user = User(
                discord_id=discord_user_id,
                discord_username=f"User_{discord_user_id[:6]}",
                coin_balance=Decimal("0.00")
            )
            db.add(user)
            await db.flush()

        item_stmt = select(RewardItem).where(RewardItem.id == item_id, RewardItem.is_active == True)
        item = (await db.execute(item_stmt)).scalar_one_or_none()

        if not item:
            return False, "Reward item not found or unavailable", None

        if user.coin_balance < item.coin_price:
            return False, f"Insufficient balance. Required: {item.coin_price} Coins, Current: {user.coin_balance} Coins", None

        user.coin_balance -= item.coin_price

        ledger_entry = CoinLedger(
            discord_user_id=discord_user_id,
            amount=-item.coin_price,
            type="shop_purchase",
            reference_id=str(item.id),
            description=f"Purchased reward: {item.name}"
        )
        db.add(ledger_entry)
        await db.commit()

        return True, f"Successfully purchased {item.name}!", item
