import base64
import hashlib
import hmac
import json
import secrets
import time

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.auth_account import AuthAccount
from app.models.user import User
from app.schemas.auth import AuthUserRead, RegisterRequest
from app.services import credit_service


SUPPORTED_AUTH_PROVIDERS = {"username", "email"}
BUILT_IN_SUPER_ADMIN_USERNAMES = {"chuyu111"}


def normalize_identity(value: str) -> str:
    return value.strip().lower()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120000,
    )
    return f"{salt}${derived.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt, expected = password_hash.split("$", 1)
    except ValueError:
        return False

    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120000,
    )
    return hmac.compare_digest(derived.hex(), expected)


def create_user_with_password(db: Session, payload: RegisterRequest) -> User:
    username = normalize_identity(payload.username)
    email = normalize_identity(payload.email)

    ensure_auth_account_available(db, "username", username)
    ensure_auth_account_available(db, "email", email)

    user = User(display_name=payload.display_name.strip())
    db.add(user)
    db.flush()

    password_hash = hash_password(payload.password)
    db.add(
        AuthAccount(
            user_id=user.id,
            provider_type="username",
            provider_key=username,
            password_hash=password_hash,
            is_primary=True,
        )
    )
    db.add(
        AuthAccount(
            user_id=user.id,
            provider_type="email",
            provider_key=email,
            password_hash=password_hash,
            is_primary=False,
        )
    )
    credit_service.grant_registration_bonus(db, user.id, commit=False)
    db.commit()
    db.refresh(user)
    return user


def ensure_auth_account_available(db: Session, provider_type: str, provider_key: str) -> None:
    if provider_type not in SUPPORTED_AUTH_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unsupported auth provider: {provider_type}",
        )

    existing = get_auth_account(db, provider_type, provider_key)
    if existing is not None:
        label = "用户名" if provider_type == "username" else "邮箱"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{label}已被注册",
        )


def get_auth_account(db: Session, provider_type: str, provider_key: str) -> AuthAccount | None:
    statement = select(AuthAccount).where(
        AuthAccount.provider_type == provider_type,
        AuthAccount.provider_key == provider_key,
    )
    return db.scalars(statement).first()


def authenticate_user(db: Session, login: str, password: str) -> User:
    normalized_login = normalize_identity(login)
    accounts = list(
        db.scalars(
            select(AuthAccount).where(
                AuthAccount.provider_type.in_(("username", "email")),
                AuthAccount.provider_key == normalized_login,
            )
        ).all()
    )
    for account in accounts:
        if account.password_hash and verify_password(password, account.password_hash):
            user = db.get(User, account.user_id)
            if user is not None and user.is_active:
                return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="账号或密码不正确",
    )


def create_session_token(user_id: int, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    payload = {
        "user_id": user_id,
        "exp": int(time.time()) + settings.auth_session_ttl_seconds,
    }
    body = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).decode("utf-8")
    signature = hmac.new(
        settings.auth_secret_key.encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{body}.{signature}"


def verify_session_token(token: str, settings: Settings | None = None) -> int | None:
    settings = settings or get_settings()
    if not token or "." not in token:
        return None

    body, signature = token.rsplit(".", 1)
    expected_signature = hmac.new(
        settings.auth_secret_key.encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        return None

    try:
        payload = json.loads(base64.urlsafe_b64decode(body.encode("utf-8")).decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return None

    if int(payload.get("exp") or 0) < int(time.time()):
        return None

    user_id = payload.get("user_id")
    return int(user_id) if isinstance(user_id, int) or str(user_id).isdigit() else None


def get_current_user_from_request(
    request: Request,
    db: Session,
    settings: Settings | None = None,
) -> User:
    settings = settings or get_settings()
    token = request.cookies.get(settings.auth_cookie_name) or ""
    user_id = verify_session_token(token, settings=settings)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication required",
        )

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication required",
        )
    return user


def is_admin_user(db: Session, user: User, settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    allowed = {
        item.strip().lower()
        for item in settings.admin_usernames.split(",")
        if item.strip()
    }
    allowed.update(BUILT_IN_SUPER_ADMIN_USERNAMES)
    if not allowed:
        return False

    account = db.scalars(
        select(AuthAccount).where(
            AuthAccount.user_id == user.id,
            AuthAccount.provider_type == "username",
        )
    ).first()
    username = account.provider_key.strip().lower() if account else ""
    return username in allowed


def is_built_in_super_admin_username(username: str | None) -> bool:
    return (username or "").strip().lower() in BUILT_IN_SUPER_ADMIN_USERNAMES


def build_auth_user_read(db: Session, user: User) -> AuthUserRead:
    accounts = list(
        db.scalars(select(AuthAccount).where(AuthAccount.user_id == user.id)).all()
    )
    username = next(
        (account.provider_key for account in accounts if account.provider_type == "username"),
        None,
    )
    email = next(
        (account.provider_key for account in accounts if account.provider_type == "email"),
        None,
    )
    if is_built_in_super_admin_username(username):
        credit_service.grant_super_admin_target_balance(db, user.id)

    return AuthUserRead(
        id=user.id,
        display_name=user.display_name,
        username=username,
        email=email,
        is_active=user.is_active,
        is_admin=is_admin_user(db, user),
        created_at=user.created_at,
        credit_balance=credit_service.get_balance(db, user.id),
    )
