from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    from app.models import account_strategy_context  # noqa: F401
    from app.models import gateway_provider  # noqa: F401
    from app.models import generation_record  # noqa: F401
    from app.models import project  # noqa: F401
    from app.models import script  # noqa: F401
    from app.models import topic  # noqa: F401

    # Database schema is managed by Alembic migrations.
    # Importing models here keeps metadata registration explicit for callers.
    return None
