from pydantic import BaseModel
from datetime import datetime


# ==========================================================
# Transaction Schemas
# ==========================================================

class TransactionCreate(BaseModel):
    user_id: str
    amount: float
    type: str


class TransactionResponse(BaseModel):
    id: str
    user_id: str
    amount: float
    type: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# ==========================================================
# AI Summary Schemas
# ==========================================================

class SummaryCreate(BaseModel):
    text: str


class SummaryResponse(BaseModel):
    id: str
    input_text: str
    output_summary: str
    created_at: datetime

    class Config:
        from_attributes = True
