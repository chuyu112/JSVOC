from __future__ import annotations

import math
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.credit import CreditAccount, CreditTransaction
from app.models.generation_task import GenerationTask
from app.services.video_model_catalog import video_model_pricing


CREDIT_PER_YUAN = 100
REGISTRATION_BONUS_CREDITS = 2000
INVITE_BONUS_CREDITS = 2000
SUPER_ADMIN_TARGET_CREDITS = 1_000_000
PURCHASE_PACKAGES = [
    {"credits": 10000, "price_yuan": 100, "title": "10000 积分包"},
]

TEXT_GENERATION_COST = 20
STRATEGY_GENERATION_COST = 20
STRATEGY_CREDITS_PER_MILLION_TOKENS = 100
TOPIC_GENERATION_COST = 20
TOPIC_CREDITS_PER_MILLION_TOKENS = 100
AI_CHAT_MIN_GENERATION_COST = 10
AI_CHAT_CREDITS_PER_MILLION_TOKENS = 100
IMAGE_GENERATION_COST = 200

VIDEO_PRICING_YUAN_PER_SECOND: dict[str, dict[str, float]] = {
    "doubao-seedance-2-0-260128": {"480p": 7 / 15, "720p": 1.0, "1080p": 37 / 15},
    "doubao-seedance-2-0-fast-260128": {"480p": 5.6 / 15, "720p": 0.8},
    "seedance-2.0": {"480p": 7 / 15, "720p": 1.0, "1080p": 37 / 15},
    "seedance-2.0-fast": {"480p": 5.6 / 15, "720p": 0.8},
}


def get_or_create_account(db: Session, user_id: int) -> CreditAccount:
    account = db.scalars(select(CreditAccount).where(CreditAccount.user_id == user_id)).first()
    if account is not None:
        return account

    account = CreditAccount(user_id=user_id, balance=0, total_granted=0, total_spent=0)
    db.add(account)
    db.flush()
    return account


def get_balance(db: Session, user_id: int) -> int:
    return get_or_create_account(db, user_id).balance


def list_transactions(db: Session, user_id: int, *, skip: int = 0, limit: int = 100) -> list[CreditTransaction]:
    statement = (
        select(CreditTransaction)
        .where(CreditTransaction.user_id == user_id)
        .order_by(CreditTransaction.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def record_transaction(
    db: Session,
    *,
    user_id: int,
    amount: int,
    transaction_type: str,
    reason: str,
    reference_type: str | None = None,
    reference_id: int | None = None,
    metadata: dict[str, Any] | None = None,
    commit: bool = True,
) -> CreditTransaction:
    account = get_or_create_account(db, user_id)
    balance_after = account.balance + amount
    if balance_after < 0:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"积分不足，当前余额 {account.balance}，需要 {abs(amount)} 积分",
        )

    account.balance = balance_after
    if amount > 0:
        account.total_granted += amount
    elif amount < 0:
        account.total_spent += abs(amount)

    transaction = CreditTransaction(
        account_id=account.id,
        user_id=user_id,
        amount=amount,
        balance_after=balance_after,
        transaction_type=transaction_type,
        reason=reason,
        reference_type=reference_type,
        reference_id=reference_id,
        transaction_metadata=metadata or {},
    )
    db.add(transaction)
    db.flush()

    if commit:
        db.commit()
        db.refresh(account)
        db.refresh(transaction)
    return transaction


def grant_registration_bonus(db: Session, user_id: int, *, commit: bool = True) -> CreditTransaction | None:
    existing = db.scalars(
        select(CreditTransaction).where(
            CreditTransaction.user_id == user_id,
            CreditTransaction.transaction_type == "registration_bonus",
        )
    ).first()
    if existing is not None:
        return existing

    return record_transaction(
        db,
        user_id=user_id,
        amount=REGISTRATION_BONUS_CREDITS,
        transaction_type="registration_bonus",
        reason="new_user_registration",
        reference_type="user",
        reference_id=user_id,
        metadata={"value_yuan": REGISTRATION_BONUS_CREDITS / CREDIT_PER_YUAN},
        commit=commit,
    )


def grant_super_admin_target_balance(db: Session, user_id: int, *, commit: bool = True) -> CreditTransaction | None:
    existing_initial_grant = db.scalars(
        select(CreditTransaction).where(
            CreditTransaction.user_id == user_id,
            CreditTransaction.transaction_type == "super_admin_grant",
            CreditTransaction.reference_type == "user",
            CreditTransaction.reference_id == user_id,
        )
    ).first()
    if existing_initial_grant is not None:
        return None

    account = get_or_create_account(db, user_id)
    amount = SUPER_ADMIN_TARGET_CREDITS - account.balance
    if amount <= 0:
        return None

    return record_transaction(
        db,
        user_id=user_id,
        amount=amount,
        transaction_type="super_admin_grant",
        reason="super_admin_target_balance",
        reference_type="user",
        reference_id=user_id,
        metadata={"target_balance": SUPER_ADMIN_TARGET_CREDITS},
        commit=commit,
    )


def ensure_sufficient_credits(db: Session, user_id: int, cost: int) -> None:
    if cost <= 0:
        return
    balance = get_balance(db, user_id)
    if balance < cost:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"积分不足，当前余额 {balance}，需要 {cost} 积分",
        )


def charge_credits(
    db: Session,
    *,
    user_id: int,
    cost: int,
    reason: str,
    reference_type: str | None = None,
    reference_id: int | None = None,
    metadata: dict[str, Any] | None = None,
    commit: bool = True,
) -> CreditTransaction | None:
    if cost <= 0:
        return None
    return record_transaction(
        db,
        user_id=user_id,
        amount=-cost,
        transaction_type="spend",
        reason=reason,
        reference_type=reference_type,
        reference_id=reference_id,
        metadata=metadata,
        commit=commit,
    )


def refund_credits(
    db: Session,
    *,
    user_id: int,
    amount: int,
    reason: str,
    reference_type: str | None = None,
    reference_id: int | None = None,
    metadata: dict[str, Any] | None = None,
    commit: bool = True,
) -> CreditTransaction | None:
    if amount <= 0:
        return None
    return record_transaction(
        db,
        user_id=user_id,
        amount=amount,
        transaction_type="refund",
        reason=reason,
        reference_type=reference_type,
        reference_id=reference_id,
        metadata=metadata,
        commit=commit,
    )


def refund_generation_task_credits(db: Session, task_id: int, *, reason: str) -> CreditTransaction | None:
    task = db.get(GenerationTask, task_id)
    if task is None or task.user_id is None or not task.credit_cost:
        return None

    existing = db.scalars(
        select(CreditTransaction).where(
            CreditTransaction.transaction_type == "refund",
            CreditTransaction.reference_type == "generation_task",
            CreditTransaction.reference_id == task_id,
        )
    ).first()
    if existing is not None:
        return existing

    return refund_credits(
        db,
        user_id=task.user_id,
        amount=task.credit_cost,
        reason=reason,
        reference_type="generation_task",
        reference_id=task_id,
        metadata={"refund_of_transaction_id": task.credit_transaction_id},
    )


def image_generation_cost(image_count: int, *, mode: str) -> int:
    del image_count, mode
    return IMAGE_GENERATION_COST


def ai_chat_generation_cost(usage: dict[str, Any] | None) -> int:
    return token_metered_generation_cost(
        usage,
        credits_per_million=AI_CHAT_CREDITS_PER_MILLION_TOKENS,
        minimum=AI_CHAT_MIN_GENERATION_COST,
    )


def topic_generation_cost(usage: dict[str, Any] | None) -> int:
    return token_metered_generation_cost(
        usage,
        credits_per_million=TOPIC_CREDITS_PER_MILLION_TOKENS,
        unit=10,
    )


def strategy_generation_cost(usage: dict[str, Any] | None) -> int:
    return token_metered_generation_cost(
        usage,
        credits_per_million=STRATEGY_CREDITS_PER_MILLION_TOKENS,
        unit=10,
    )


def token_metered_generation_cost(
    usage: dict[str, Any] | None,
    *,
    credits_per_million: int,
    minimum: int = 0,
    unit: int = 1,
) -> int:
    total_tokens = token_usage_total(usage)
    token_cost = int(math.ceil(total_tokens * credits_per_million / 1_000_000))
    cost = max(minimum, token_cost)
    if unit <= 1:
        return cost
    return int(math.ceil(cost / unit) * unit)


def token_usage_total(usage: dict[str, Any] | None) -> int:
    usage = usage or {}
    total_tokens = usage_int(usage.get("total_tokens"))
    if total_tokens > 0:
        return total_tokens

    prompt_tokens = usage_int(usage.get("prompt_tokens"))
    completion_tokens = usage_int(usage.get("completion_tokens"))
    if prompt_tokens or completion_tokens:
        return prompt_tokens + completion_tokens

    input_tokens = usage_int(usage.get("input_tokens"))
    output_tokens = usage_int(usage.get("output_tokens"))
    return input_tokens + output_tokens


def usage_int(value: Any) -> int:
    try:
        return max(0, int(float(value or 0)))
    except (TypeError, ValueError):
        return 0


def video_generation_cost(options: dict[str, Any] | None) -> int:
    options = options or {}
    model = str(options.get("model") or "")
    resolution = str(options.get("resolution") or "720p")
    pricing = video_model_pricing(model) or VIDEO_PRICING_YUAN_PER_SECOND.get(model)
    if pricing is None:
        raise ValueError(f"unsupported video model: {model or 'default'}")
    yuan_per_second = pricing.get(resolution)
    if yuan_per_second is None:
        raise ValueError(f"video model {model or 'default'} does not support {resolution}")
    duration = 5 if options.get("duration_mode") == "smart" else int(options.get("duration_seconds") or 5)
    count = int(options.get("count") or 1)
    yuan_cost = max(1, duration) * max(1, count) * yuan_per_second
    raw_credits = int(math.ceil(yuan_cost * CREDIT_PER_YUAN))
    return int(math.ceil(raw_credits / 10) * 10)
