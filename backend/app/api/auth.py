from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.auth import AuthSessionResponse, LoginRequest, RegisterRequest
from app.services import auth_service


router = APIRouter(prefix="/api/auth", tags=["auth"])


def success_response(data: object, message: str = "") -> dict[str, object]:
    return {"success": True, "data": data, "message": message}


def write_auth_cookie(response: Response, session_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=session_token,
        max_age=settings.auth_session_ttl_seconds,
        httponly=True,
        samesite=settings.auth_cookie_samesite,
        secure=settings.auth_cookie_secure,
        path="/",
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    user = auth_service.create_user_with_password(db, payload)
    session_token = auth_service.create_session_token(user.id)
    write_auth_cookie(response, session_token)
    data = AuthSessionResponse(user=auth_service.build_auth_user_read(db, user))
    return success_response(data.model_dump(mode="json"), "registered")


@router.post("/login")
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    user = auth_service.authenticate_user(db, payload.login, payload.password)
    session_token = auth_service.create_session_token(user.id)
    write_auth_cookie(response, session_token)
    data = AuthSessionResponse(user=auth_service.build_auth_user_read(db, user))
    return success_response(data.model_dump(mode="json"), "logged in")


@router.post("/logout")
def logout(response: Response) -> dict[str, object]:
    settings = get_settings()
    response.delete_cookie(key=settings.auth_cookie_name, path="/")
    return success_response({"logged_out": True}, "logged out")


@router.get("/me")
def me(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    user = auth_service.get_current_user_from_request(request, db)
    data = AuthSessionResponse(user=auth_service.build_auth_user_read(db, user))
    return success_response(data.model_dump(mode="json"))
