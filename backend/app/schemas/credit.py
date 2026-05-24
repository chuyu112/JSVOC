from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CreditAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    balance: int
    total_granted: int
    total_spent: int
    created_at: datetime
    updated_at: datetime


class CreditTransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    amount: int
    balance_after: int
    transaction_type: str
    reason: str
    reference_type: str | None = None
    reference_id: int | None = None
    transaction_metadata: dict
    created_at: datetime


class CreditPackageRead(BaseModel):
    credits: int
    price_yuan: int
    title: str
