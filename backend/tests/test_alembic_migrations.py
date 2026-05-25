import tempfile
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

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "migration.db"
            database_url = f"sqlite:///{db_path.as_posix()}"

            config = Config(str(backend_dir / "alembic.ini"))
            config.set_main_option("script_location", str(backend_dir / "alembic"))
            config.set_main_option("sqlalchemy.url", database_url)

            command.upgrade(config, "head")

            engine = create_engine(database_url)
            try:
                inspector = inspect(engine)
                self.assertEqual(
                    {
                        "account_strategy_contexts",
                        "auth_accounts",
                        "credit_accounts",
                        "credit_transactions",
                        "digital_assets",
                        "generation_records",
                        "generation_tasks",
                        "hot_copy_materials",
                        "hot_copy_rewrites",
                        "llm_channels",
                        "projects",
                        "project_reference_images",
                        "scripts",
                        "topics",
                        "users",
                    },
                    set(inspector.get_table_names()) - {"alembic_version"},
                )
                material_columns = {column["name"] for column in inspector.get_columns("hot_copy_materials")}
                self.assertTrue(
                    {
                        "id",
                        "user_id",
                        "project_id",
                        "platform",
                        "source_type",
                        "source_url",
                        "account_name",
                        "account_home_url",
                        "cover_url",
                        "title",
                        "original_script",
                        "metrics_json",
                        "analysis_json",
                        "created_at",
                        "updated_at",
                    }.issubset(material_columns)
                )
                rewrite_columns = {column["name"] for column in inspector.get_columns("hot_copy_rewrites")}
                self.assertTrue(
                    {
                        "id",
                        "material_id",
                        "user_id",
                        "project_id",
                        "rewrite_mode",
                        "duration",
                        "conversion_goal",
                        "input_json",
                        "output_json",
                        "generation_record_id",
                        "created_at",
                    }.issubset(rewrite_columns)
                )
            finally:
                engine.dispose()

    def test_init_db_does_not_create_schema_directly(self) -> None:
        with patch.object(Base.metadata, "create_all") as create_all:
            init_db()

        create_all.assert_not_called()

    def test_database_url_environment_overrides_alembic_ini_default(self) -> None:
        backend_dir = Path(__file__).resolve().parents[1]

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "environment-url.db"
            database_url = f"sqlite:///{db_path.as_posix()}"

            config = Config(str(backend_dir / "alembic.ini"))
            config.set_main_option("script_location", str(backend_dir / "alembic"))

            with patch.dict("os.environ", {"DATABASE_URL": database_url}):
                command.upgrade(config, "head")

            self.assertTrue(db_path.exists())


if __name__ == "__main__":
    unittest.main()
