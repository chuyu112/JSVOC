from __future__ import annotations

import argparse
import os
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import AuthAccount, CreditAccount, CreditTransaction, LLMChannel, User
from app.schemas.llm_channel import normalize_provider
from app.services import credit_service, llm_channel_service


DEFAULT_BASE_URL = "http://43.173.105.8:8080/v1"
DEFAULT_CHAT_MODEL = "gpt-5.5"
DEFAULT_IMAGE_MODEL = "gpt-image-2"
DEFAULT_TARGET_BALANCE = 20_000
DEFAULT_SUPER_ADMIN_USERNAME = "chuyu111"


@dataclass(frozen=True)
class ChannelResult:
    id: int
    name: str
    purpose: str
    provider: str
    base_url: str
    model: str
    is_active: bool
    has_api_key: bool


@dataclass(frozen=True)
class CreditResult:
    user_id: int
    display_name: str
    previous_balance: int
    current_balance: int
    granted_amount: int


def configure_kakayiduo_channels(
    db: Session,
    *,
    api_key: str,
    base_url: str = DEFAULT_BASE_URL,
    chat_model: str = DEFAULT_CHAT_MODEL,
    image_model: str = DEFAULT_IMAGE_MODEL,
) -> list[ChannelResult]:
    if not api_key.strip():
        raise ValueError("KAKAYIDUO_API_KEY is required to create or update kakayiduo channels")

    return [
        upsert_kakayiduo_channel(
            db,
            purpose=llm_channel_service.CHANNEL_PURPOSE_CHAT,
            name="Kakayiduo Chat",
            base_url=base_url,
            api_key=api_key,
            model=chat_model,
        ),
        upsert_kakayiduo_channel(
            db,
            purpose=llm_channel_service.CHANNEL_PURPOSE_IMAGE,
            name="Kakayiduo Image",
            base_url=base_url,
            api_key=api_key,
            model=image_model,
        ),
    ]


def upsert_kakayiduo_channel(
    db: Session,
    *,
    purpose: str,
    name: str,
    base_url: str,
    api_key: str,
    model: str,
) -> ChannelResult:
    channel = find_kakayiduo_channel(db, purpose, name)
    if channel is None:
        channel = LLMChannel(
            name=name,
            purpose=purpose,
            provider="kakayiduo",
            base_url=base_url.strip(),
            api_key=api_key.strip(),
            model=model.strip(),
            is_active=False,
        )
        db.add(channel)
        db.flush()
    else:
        channel.name = name
        channel.provider = "kakayiduo"
        channel.base_url = base_url.strip()
        channel.api_key = api_key.strip()
        channel.model = model.strip()

    llm_channel_service.deactivate_channels_for_purpose(db, purpose)
    channel.is_active = True
    db.flush()
    return ChannelResult(
        id=channel.id,
        name=channel.name,
        purpose=channel.purpose,
        provider=normalize_provider(channel.provider),
        base_url=channel.base_url,
        model=channel.model,
        is_active=channel.is_active,
        has_api_key=bool(channel.api_key.strip()),
    )


def find_kakayiduo_channel(db: Session, purpose: str, preferred_name: str) -> LLMChannel | None:
    channels = list(db.scalars(select(LLMChannel).where(LLMChannel.purpose == purpose)).all())
    kakayiduo_channels = [
        channel
        for channel in channels
        if llm_channel_service.normalized_channel_provider(channel.provider) == "kakayiduo"
    ]
    return (
        next((channel for channel in kakayiduo_channels if channel.name == preferred_name), None)
        or next((channel for channel in kakayiduo_channels if channel.is_active), None)
        or (kakayiduo_channels[0] if kakayiduo_channels else None)
    )


def top_up_user_to_balance(
    db: Session,
    *,
    target_user: str | None = None,
    user_id: int | None = None,
    target_balance: int = DEFAULT_TARGET_BALANCE,
) -> CreditResult:
    user = get_target_user(db, target_user=target_user, user_id=user_id)
    account = credit_service.get_or_create_account(db, user.id)
    previous_balance = account.balance
    amount = target_balance - previous_balance
    if amount > 0:
        credit_service.record_transaction(
            db,
            user_id=user.id,
            amount=amount,
            transaction_type="admin_grant",
            reason="admin_top_up_to_target",
            reference_type="user",
            reference_id=user.id,
            metadata={"target_balance": target_balance},
            commit=False,
        )
        db.flush()
    return CreditResult(
        user_id=user.id,
        display_name=user.display_name,
        previous_balance=previous_balance,
        current_balance=credit_service.get_balance(db, user.id),
        granted_amount=max(amount, 0),
    )


def get_target_user(db: Session, *, target_user: str | None, user_id: int | None) -> User:
    if user_id is not None:
        user = db.get(User, user_id)
        if user is None:
            raise ValueError(f"user id not found: {user_id}")
        return user

    target = (target_user or "").strip()
    if not target:
        raise ValueError("target user display name, username, email, or --user-id is required")

    display_matches = list(db.scalars(select(User).where(User.display_name == target)).all())
    if len(display_matches) == 1:
        return display_matches[0]
    if len(display_matches) > 1:
        ids = ", ".join(str(user.id) for user in display_matches)
        raise ValueError(f"multiple users match display name {target!r}; rerun with --user-id. IDs: {ids}")

    account = db.scalars(
        select(AuthAccount).where(
            AuthAccount.provider_type.in_(("username", "email")),
            AuthAccount.provider_key == target.lower(),
        )
    ).first()
    if account is not None:
        user = db.get(User, account.user_id)
        if user is not None:
            return user

    raise ValueError(f"user not found: {target}")


def ensure_super_admin_target_balance(
    db: Session,
    *,
    username: str = DEFAULT_SUPER_ADMIN_USERNAME,
) -> CreditResult | None:
    account = db.scalars(
        select(AuthAccount).where(
            AuthAccount.provider_type == "username",
            AuthAccount.provider_key == username.strip().lower(),
        )
    ).first()
    if account is None:
        return None

    user = db.get(User, account.user_id)
    if user is None:
        return None

    credit_account = credit_service.get_or_create_account(db, user.id)
    previous_balance = credit_account.balance
    transaction = credit_service.grant_super_admin_target_balance(db, user.id, commit=False)
    db.flush()
    return CreditResult(
        user_id=user.id,
        display_name=user.display_name,
        previous_balance=previous_balance,
        current_balance=credit_service.get_balance(db, user.id),
        granted_amount=transaction.amount if transaction is not None else 0,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Configure kakayiduo chat/image channels and top up a user's credits.",
    )
    parser.add_argument("--base-url", default=os.getenv("KAKAYIDUO_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--api-key-env", default="KAKAYIDUO_API_KEY")
    parser.add_argument("--chat-model", default=os.getenv("KAKAYIDUO_CHAT_MODEL", DEFAULT_CHAT_MODEL))
    parser.add_argument("--image-model", default=os.getenv("KAKAYIDUO_IMAGE_MODEL", DEFAULT_IMAGE_MODEL))
    parser.add_argument("--target-user", default=os.getenv("CREDIT_TARGET_USER", ""))
    parser.add_argument("--user-id", type=int, default=None)
    parser.add_argument("--target-balance", type=int, default=DEFAULT_TARGET_BALANCE)
    parser.add_argument("--super-admin-username", default=os.getenv("SUPER_ADMIN_USERNAME", DEFAULT_SUPER_ADMIN_USERNAME))
    parser.add_argument("--skip-channels", action="store_true")
    parser.add_argument("--skip-credit", action="store_true")
    parser.add_argument("--skip-super-admin", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    api_key = os.getenv(args.api_key_env, "")

    with SessionLocal() as db:
        channel_results: list[ChannelResult] = []
        credit_result: CreditResult | None = None
        super_admin_result: CreditResult | None = None
        if not args.skip_channels:
            channel_results = configure_kakayiduo_channels(
                db,
                api_key=api_key,
                base_url=args.base_url,
                chat_model=args.chat_model,
                image_model=args.image_model,
            )
        if not args.skip_credit:
            credit_result = top_up_user_to_balance(
                db,
                target_user=args.target_user,
                user_id=args.user_id,
                target_balance=args.target_balance,
            )
        if not args.skip_super_admin:
            super_admin_result = ensure_super_admin_target_balance(
                db,
                username=args.super_admin_username,
            )
        db.commit()

    for result in channel_results:
        print(
            "channel "
            f"id={result.id} purpose={result.purpose} provider={result.provider} "
            f"base_url={result.base_url} model={result.model} active={result.is_active} "
            f"has_api_key={result.has_api_key}"
        )
    if credit_result is not None:
        print(
            "credits "
            f"user_id={credit_result.user_id} display_name={credit_result.display_name} "
            f"previous={credit_result.previous_balance} current={credit_result.current_balance} "
            f"granted={credit_result.granted_amount}"
        )
    if super_admin_result is not None:
        print(
            "super_admin "
            f"user_id={super_admin_result.user_id} display_name={super_admin_result.display_name} "
            f"previous={super_admin_result.previous_balance} current={super_admin_result.current_balance} "
            f"granted={super_admin_result.granted_amount}"
        )


if __name__ == "__main__":
    main()
