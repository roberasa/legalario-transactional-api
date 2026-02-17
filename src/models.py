from sqlalchemy import Column, String, Float, DateTime, Text
from datetime import datetime
import uuid

from src.database import Base


# ==========================================================
# Transaction Model
# ==========================================================

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    type = Column(String, nullable=False)
    status = Column(String, default="pendiente")
    idempotency_key = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ==========================================================
# AI Summary Model
# ==========================================================

class SummaryRequest(Base):
    __tablename__ = "summary_requests"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    input_text = Column(Text, nullable=False)
    output_summary = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
