import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import account_strategy_context  # noqa: F401
from app.models import generation_record  # noqa: F401
from app.models import project  # noqa: F401
from app.models.generation_record import GenerationRecord


class StrategyBundleExecutionPlanApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)
        self.register_user("owner", "owner@example.com")

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def register_user(self, username: str, email: str) -> None:
        response = self.client.post(
            "/api/auth/register",
            json={
                "display_name": username.title(),
                "username": username,
                "email": email,
                "password": "StrongPass123",
            },
        )
        self.assertEqual(response.status_code, 201)

    def test_mock_provider_generates_30_day_execution_plan_from_bundle_and_record(self) -> None:
        create_response = self.client.post(
            "/api/projects",
            json={
                "project_name": "四会翡翠账号",
                "industry": "珠宝",
                "sub_industry": "翡翠",
                "product": "翡翠",
                "personal_intro": "在四会卖翡翠多年，为人靠谱",
                "target_audience": "喜欢翡翠，想买翡翠的人",
                "platforms": ["抖音", "视频号", "快手", "小红书"],
                "current_stage": "冷启动",
            },
        )
        project_id = create_response.json()["data"]["id"]

        with patch.dict("os.environ", {"LLM_PROVIDER": "mock", "LLM_MODEL": "mock-model"}):
            from app.core.config import get_settings

            get_settings.cache_clear()
            response = self.client.post(
                "/api/strategy/account-package-execution-plan/generate",
                json={"project_id": project_id},
            )
            get_settings.cache_clear()

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        execution_plan = body["data"]["execution_plan"]
        self.assertEqual(execution_plan["cycle"], "30天")
        self.assertGreaterEqual(len(execution_plan["weekly_plan"]), 4)
        self.assertEqual(len(execution_plan["daily_plan"]), 30)

        for day in execution_plan["daily_plan"]:
            self.assertTrue(day["task"])
            self.assertTrue(day["topic"])
            self.assertTrue(day["shooting_task"])
            self.assertTrue(day["review_metrics"])

        with self.SessionLocal() as db:
            records = db.scalars(
                select(GenerationRecord).where(
                    GenerationRecord.project_id == project_id,
                    GenerationRecord.module_name == "strategy_bundle",
                )
            ).all()

        self.assertEqual(len(records), 1)
        self.assertIn("account_package", records[0].output_data["data"])
        self.assertIn("execution_plan", records[0].output_data["data"])


if __name__ == "__main__":
    unittest.main()
