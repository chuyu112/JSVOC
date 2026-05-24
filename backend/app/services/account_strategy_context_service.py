from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.account_strategy_context import AccountStrategyContext
from app.schemas.account_strategy_context import AccountStrategyContextCreate


def create_account_strategy_context(
    db: Session,
    context_in: AccountStrategyContextCreate,
) -> AccountStrategyContext:
    context = AccountStrategyContext(**context_in.model_dump(exclude={"rubric_notes"}))
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


def get_project_account_strategy_contexts(
    db: Session,
    project_id: int,
) -> list[AccountStrategyContext]:
    statement = select(AccountStrategyContext).where(AccountStrategyContext.project_id == project_id)
    return list(db.scalars(statement).all())


def delete_account_strategy_contexts_by_ids(db: Session, context_ids: list[int]) -> None:
    if not context_ids:
        return
    contexts = list(
        db.scalars(select(AccountStrategyContext).where(AccountStrategyContext.id.in_(context_ids))).all()
    )
    for context in contexts:
        db.delete(context)
    db.commit()
