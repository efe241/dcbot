from sqlalchemy import Column, Integer, String, Boolean, Numeric, Text, DateTime, func
from backend.database import Base
from decimal import Decimal

class RewardItem(Base):
    __tablename__ = "reward_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    coin_price = Column(Numeric(14, 2), nullable=False)
    reward_type = Column(String(50), nullable=False)  # role, vip, giveaway_ticket, xp_boost, custom
    role_id = Column(String(32), nullable=True)  # Discord Role ID if applicable
    duration_days = Column(Integer, nullable=True)  # Days if temporary perk
    icon_emoji = Column(String(20), default="🎁", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<RewardItem name={self.name} price={self.coin_price}>"
