import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import account_strategy_context  # noqa: F401
from app.models import generation_record  # noqa: F401
from app.models import project  # noqa: F401
from app.models.generation_record import GenerationRecord


class TopicsApiTest(unittest.TestCase):
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

    def test_mock_provider_generates_and_saves_20_topics(self) -> None:
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

        response = self.client.post(
            "/api/creation/topics/generate",
            json={"project_id": project_id, "platform": "抖音", "goal": "获客", "count": 20},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        topics = body["data"]["topics"]
        self.assertEqual(len(topics), 20)

        for item in topics:
            self.assertIsInstance(item["id"], int)
            self.assertTrue(item["title"])
            self.assertEqual(item["platform"], "抖音")
            self.assertTrue(item["content_type"])
            self.assertEqual(item["goal"], "获客")
            self.assertTrue(item["topic_data"]["user_pain_point"])
            self.assertTrue(item["topic_data"]["hook"])
            self.assertTrue(item["topic_data"]["shooting_suggestion"])
            self.assertTrue(item["topic_data"]["conversion_method"])
            self.assertGreaterEqual(item["score"], 80)

        with self.SessionLocal() as db:
            topic_count = db.execute(
                text("select count(*) from topics where project_id = :project_id"),
                {"project_id": project_id},
            ).scalar_one()
            records = db.scalars(
                select(GenerationRecord).where(
                    GenerationRecord.project_id == project_id,
                    GenerationRecord.module_name == "topics",
                )
            ).all()

        self.assertEqual(topic_count, 20)
        self.assertEqual(len(records), 1)


if __name__ == "__main__":
    unittest.main()
