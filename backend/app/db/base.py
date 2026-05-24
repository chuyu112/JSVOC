from sqlalchemy.orm import DeclarativeBase

from app.core.datetime_utils import utcnow_naive  # noqa: F401 - re-exported for convenience


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    from app.models import account_strategy_context  # noqa: F401
    from app.models import auth_account  # noqa: F401
    from app.models import credit  # noqa: F401
    from app.models import digital_asset  # noqa: F401
    from app.models import generation_record  # noqa: F401
    from app.models import generation_task  # noqa: F401
    from app.models import project  # noqa: F401
    from app.models import project_reference_image  # noqa: F401
    from app.models import script  # noqa: F401
    from app.models import topic  # noqa: F401
    from app.models import user  # noqa: F401

    # Database schema is managed by Alembic migrations.
    # Importing models here keeps metadata registration explicit for callers.
    return None
