import unittest
from pathlib import Path
from unittest.mock import patch

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.db.base import Base, init_db


class AlembicMigrationsTest(unittest.TestCase):
    def test_upgrade_head_creates_current_mvp_tables_on_sqlite(self) -> None:
        backend_dir = Path(__file__).resolve().parents[1]

        engine = create_engine("sqlite:///:memory:")
        try:
            config = Config(str(backend_dir / "alembic.ini"))
            config.set_main_option("script_location", str(backend_dir / "alembic"))
            with engine.begin() as connection:
                config.attributes["connection"] = connection
                command.upgrade(config, "head")
                inspector = inspect(connection)
                table_names = set(inspector.get_table_names()) - {"alembic_version"}
        finally:
            engine.dispose()

        self.assertEqual(
            {
                "projects",
                "account_strategy_contexts",
                "generation_records",
                "gateway_providers",
                "topics",
                "scripts",
            },
            table_names,
        )

    def test_init_db_does_not_create_schema_directly(self) -> None:
        with patch.object(Base.metadata, "create_all") as create_all:
            init_db()

        create_all.assert_not_called()

    def test_database_url_environment_overrides_alembic_ini_default(self) -> None:
        backend_dir = Path(__file__).resolve().parents[1]

        config = Config(str(backend_dir / "alembic.ini"))
        config.set_main_option("script_location", str(backend_dir / "alembic"))
        config.set_main_option("sqlalchemy.url", "sqlite:///Z:/not-available/should-not-be-used.db")

        with patch.dict("os.environ", {"DATABASE_URL": "sqlite:///:memory:"}):
            command.upgrade(config, "head")


if __name__ == "__main__":
    unittest.main()
