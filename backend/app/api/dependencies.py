from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.services import auth_service


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    return auth_service.get_current_user_from_request(request, db)
