from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.account_strategy_context import AccountStrategyContext
from app.schemas.account_strategy_context import AccountStrategyContextCreate


def create_account_strategy_context(
    db: Session,
    context_in: AccountStrategyContextCreate,
) -> AccountStrategyContext:
    context = AccountStrategyContext(**context_in.model_dump())
    db.add(context)
    db.commit()
    db.refresh(context)
    return context


def get_latest_account_strategy_context(
    db: Session,
    project_id: int,
) -> AccountStrategyContext | None:
    statement = (
        select(AccountStrategyContext)
        .where(AccountStrategyContext.project_id == project_id)
        .order_by(AccountStrategyContext.created_at.desc())
        .limit(1)
    )
    return db.scalars(statement).first()
