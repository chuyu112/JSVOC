import unittest

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

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_lists_filters_and_opens_generation_records(self) -> None:
        project_id = self._create_project()
        self.client.post("/api/strategy/account-package/generate", json={"project_id": project_id})
        self.client.post("/api/strategy/execution-plan/generate", json={"project_id": project_id})
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
        self.assertEqual(len(all_records), 4)
        self.assertEqual(
            {record["module_name"] for record in all_records},
            {"account_package", "execution_plan", "topics", "script"},
        )

        project_response = self.client.get(f"/api/generation-records?project_id={project_id}")
        self.assertEqual(project_response.status_code, 200)
        self.assertEqual(len(project_response.json()["data"]), 4)

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


if __name__ == "__main__":
    unittest.main()
