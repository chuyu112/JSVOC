import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import account_strategy_context  # noqa: F401
from app.models import generation_record  # noqa: F401
from app.models import project  # noqa: F401
from app.models import script  # noqa: F401
from app.models import topic  # noqa: F401


class GenerationRecordsApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.env_patcher = patch.dict("os.environ", {"LLM_PROVIDER": "mock", "LLM_MODEL": "mock-model"})
        self.env_patcher.start()
        from app.core.config import get_settings

        get_settings.cache_clear()
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
        self.register_user(self.client, "owner", "owner@example.com")

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()
        from app.core.config import get_settings

        get_settings.cache_clear()
        self.env_patcher.stop()

    def test_lists_filters_and_opens_generation_records(self) -> None:
        project_id = self._create_project()
        self.client.post(
            "/api/strategy/account-package-execution-plan/generate",
            json={"project_id": project_id},
        )
        topic_response = self.client.post(
            "/api/creation/topics/generate",
            json={"project_id": project_id, "platform": "抖音", "goal": "获客", "count": 1},
        )
        topic_id = topic_response.json()["data"]["topics"][0]["id"]
        self.client.post(
            "/api/creation/scripts/generate",
            json={"project_id": project_id, "topic_id": topic_id},
        )

        all_response = self.client.get("/api/generation-records")
        self.assertEqual(all_response.status_code, 200)
        all_records = all_response.json()["data"]
        self.assertEqual(len(all_records), 3)
        self.assertEqual(
            {record["module_name"] for record in all_records},
            {"strategy_bundle", "topics", "script"},
        )

        project_response = self.client.get(f"/api/generation-records?project_id={project_id}")
        self.assertEqual(project_response.status_code, 200)
        self.assertEqual(len(project_response.json()["data"]), 3)

        module_response = self.client.get("/api/generation-records?module_name=topics")
        self.assertEqual(module_response.status_code, 200)
        topic_records = module_response.json()["data"]
        self.assertEqual(len(topic_records), 1)
        self.assertEqual(topic_records[0]["module_name"], "topics")
        self.assertEqual(topic_records[0]["project_id"], project_id)

        detail_response = self.client.get(f"/api/generation-records/{topic_records[0]['id']}")
        self.assertEqual(detail_response.status_code, 200)
        detail = detail_response.json()["data"]
        self.assertEqual(detail["id"], topic_records[0]["id"])
        self.assertEqual(detail["module_name"], "topics")
        self.assertTrue(detail["input_data"])
        self.assertTrue(detail["output_data"])
        self.assertIn("model_provider", detail)
        self.assertIn("token_usage", detail)
        self.assertIn("latency_ms", detail)
        self.assertIn("created_at", detail)

    def register_user(self, client: TestClient, username: str, email: str) -> None:
        response = client.post(
            "/api/auth/register",
            json={
                "display_name": username.title(),
                "username": username,
                "email": email,
                "password": "StrongPass123",
            },
        )
        self.assertEqual(response.status_code, 201)

    def _create_project(self) -> int:
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
        return int(create_response.json()["data"]["id"])

    def test_generation_records_are_filtered_by_current_user(self) -> None:
        owner_project_id = self._create_project()
        self.client.post(
            "/api/strategy/account-package-execution-plan/generate",
            json={"project_id": owner_project_id},
        )

        other_client = TestClient(app)
        self.register_user(other_client, "other", "other@example.com")
        create_response = other_client.post(
            "/api/projects",
            json={
                "project_name": "other project",
                "industry": "jewelry",
                "sub_industry": "jade",
                "product": "jade bracelet",
                "personal_intro": "other seller",
                "target_audience": "other buyers",
                "platforms": ["douyin"],
                "current_stage": "cold_start",
            },
        )
        other_project_id = create_response.json()["data"]["id"]
        other_client.post(
            "/api/strategy/account-package-execution-plan/generate",
            json={"project_id": other_project_id},
        )

        owner_records = self.client.get("/api/generation-records")
        other_records = other_client.get("/api/generation-records")

        self.assertEqual(owner_records.status_code, 200)
        self.assertEqual(other_records.status_code, 200)
        self.assertEqual(len(owner_records.json()["data"]), 1)
        self.assertEqual(len(other_records.json()["data"]), 1)
        self.assertNotEqual(owner_records.json()["data"][0]["project_id"], other_records.json()["data"][0]["project_id"])


if __name__ == "__main__":
    unittest.main()
