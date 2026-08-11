from sqlalchemy import Column, Integer, String, Numeric, Text, DateTime, func
from backend.database import Base
from decimal import Decimal

class CoinLedger(Base):
    __tablename__ = "coin_ledger"

    id = Column(Integer, primary_key=True, index=True)
    discord_user_id = Column(String(32), index=True, nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)  # positive (+) for credit, negative (-) for debit
    type = Column(String(50), nullable=False)  # survey_reward, survey_reversal, admin_reward, admin_deduction, shop_purchase
    reference_id = Column(String(128), nullable=True)  # trans_id or purchase_id
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<CoinLedger user={self.discord_user_id} amount={self.amount} type={self.type}>"
