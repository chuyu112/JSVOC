from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.credit import CreditAccountRead, CreditPackageRead, CreditTransactionRead
from app.services import auth_service, credit_service


router = APIRouter(prefix="/api/credits", tags=["credits"])


def success_response(data: object, message: str = "") -> dict[str, object]:
    return {"success": True, "data": data, "message": message}


@router.get("/balance")
def get_credit_balance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    auth_service.ensure_user_credit_entitlements(db, current_user)
    account = credit_service.get_or_create_account(db, current_user.id)
    db.commit()
    db.refresh(account)
    return success_response(CreditAccountRead.model_validate(account).model_dump(mode="json"))


@router.get("/transactions")
def get_credit_transactions(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    transactions = credit_service.list_transactions(db, current_user.id, skip=skip, limit=limit)
    return success_response(
        [CreditTransactionRead.model_validate(item).model_dump(mode="json") for item in transactions]
    )


@router.get("/packages")
def get_credit_packages() -> dict[str, object]:
    packages = [CreditPackageRead(**package).model_dump(mode="json") for package in credit_service.PURCHASE_PACKAGES]
    return success_response(packages)
