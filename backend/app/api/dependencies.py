from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.auth_account import AuthAccount
from app.models.user import User
from app.services import auth_service


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    return auth_service.get_current_user_from_request(request, db)


def get_current_admin_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    user = get_current_user(request, db)
    settings = get_settings()
    allowed = {
        item.strip().lower()
        for item in settings.admin_usernames.split(",")
        if item.strip()
    }
    account = db.scalars(
        select(AuthAccount).where(
            AuthAccount.user_id == user.id,
            AuthAccount.provider_type == "username",
        )
    ).first()
    username = account.provider_key.strip().lower() if account else ""
    if username not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="admin access required",
        )
    return user
