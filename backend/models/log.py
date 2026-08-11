from sqlalchemy import Column, Integer, String, Boolean, Numeric, Text, DateTime, func
from backend.database import Base

class PostbackLog(Base):
    __tablename__ = "postback_logs"

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String(64), nullable=True)
    trans_id = Column(String(128), nullable=True)
    user_id = Column(String(32), nullable=True)
    status = Column(Integer, nullable=True)
    amount_usd = Column(Numeric(10, 4), nullable=True)
    hash_valid = Column(Boolean, nullable=True)
    ip_whitelisted = Column(Boolean, nullable=True)
    processed = Column(Boolean, default=False, nullable=False)
    error_message = Column(Text, nullable=True)
    raw_params = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<PostbackLog id={self.id} ip={self.ip_address} trans_id={self.trans_id} processed={self.processed}>"
