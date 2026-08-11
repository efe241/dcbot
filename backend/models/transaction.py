from sqlalchemy import Column, Integer, String, Boolean, Numeric, DateTime, func
from backend.database import Base
from decimal import Decimal

class CPXTransaction(Base):
    __tablename__ = "cpx_transactions"

    id = Column(Integer, primary_key=True, index=True)
    trans_id = Column(String(128), unique=True, index=True, nullable=False)
    discord_user_id = Column(String(32), index=True, nullable=False)
    status = Column(Integer, nullable=False)  # 1 = completed, 2 = reversal
    type = Column(String(50), nullable=True)  # e.g., survey, offer
    amount_usd = Column(Numeric(10, 4), default=Decimal("0.0000"), nullable=False)
    coin_amount = Column(Numeric(14, 2), default=Decimal("0.00"), nullable=False)
    ip_click = Column(String(64), nullable=True)
    subid_1 = Column(String(255), nullable=True)
    subid_2 = Column(String(255), nullable=True)
    secure_hash_valid = Column(Boolean, default=True, nullable=False)
    risk_score = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<CPXTransaction trans_id={self.trans_id} user={self.discord_user_id} status={self.status} usd={self.amount_usd}>"
