from sqlalchemy import Column, Integer, String, Boolean, Numeric, DateTime, func
from backend.database import Base
from decimal import Decimal

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    discord_id = Column(String(32), unique=True, index=True, nullable=False)
    discord_username = Column(String(100), nullable=False)
    discord_avatar = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    coin_balance = Column(Numeric(14, 2), default=Decimal("0.00"), nullable=False)
    is_banned = Column(Boolean, default=False, nullable=False)
    risk_score = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<User {self.discord_username} ({self.discord_id}) balance={self.coin_balance}>"
