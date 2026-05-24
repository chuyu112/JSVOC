import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import account_strategy_context  # noqa: F401
from app.models import auth_account  # noqa: F401
from app.models import digital_asset  # noqa: F401
from app.models import user  # noqa: F401
from app.models import generation_record  # noqa: F401
from app.models import project  # noqa: F401
from app.models import topic  # noqa: F401
from app.models.generation_record import GenerationRecord
from app.llm.llm_gateway import LLMGatewayResponse


class ScriptsApiTest(unittest.TestCase):
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
        self.register_user("owner", "owner@example.com")

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()
        from app.core.config import get_settings

        get_settings.cache_clear()
        self.env_patcher.stop()

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
        self.current_user_id = response.json()["data"]["user"]["id"]

    def test_mock_provider_generates_and_saves_script_from_topic(self) -> None:
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
        topic_response = self.client.post(
            "/api/creation/topics/generate",
            json={"project_id": project_id, "platform": "抖音", "goal": "获客", "count": 1},
        )
        topic_id = topic_response.json()["data"]["topics"][0]["id"]

        response = self.client.post(
            "/api/creation/scripts/generate",
            json={
                "project_id": project_id,
                "topic_id": topic_id,
                "script_type": "聊观点",
                "duration": "60秒",
                "goal": "私信获客",
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        script = body["data"]["script"]
        self.assertIsInstance(script["id"], int)
        self.assertEqual(script["project_id"], project_id)
        self.assertEqual(script["topic_id"], topic_id)
        self.assertEqual(script["platform"], "抖音")
        self.assertEqual(script["script_type"], "聊观点")
        self.assertTrue(script["title"])
        self.assertTrue(script["script_data"]["hook"])
        self.assertIn("四会", script["script_content"])
        self.assertIn("翡翠", script["script_content"])
        self.assertTrue(script["shot_suggestions"])
        self.assertTrue(script["script_data"]["subtitle_points"])
        self.assertTrue(script["conversion_script"])
        self.assertTrue(script["script_data"]["comment_guidance"])
        self.assertTrue(script["script_data"]["private_message_guidance"])
        self.assertIsInstance(body["data"]["generation_record_id"], int)

        with self.SessionLocal() as db:
            script_count = db.execute(
                text("select count(*) from scripts where topic_id = :topic_id"),
                {"topic_id": topic_id},
            ).scalar_one()
            records = db.scalars(
                select(GenerationRecord).where(
                    GenerationRecord.project_id == project_id,
                    GenerationRecord.module_name == "script",
                )
            ).all()
            asset_count = db.execute(
                text("select count(*) from digital_assets where user_id = :user_id and asset_type = 'script'"),
                {"user_id": self.current_user_id},
            ).scalar_one()

        self.assertEqual(script_count, 1)
        self.assertEqual(len(records), 1)
        self.assertEqual(asset_count, 1)

    def test_generate_script_uses_compact_request_to_avoid_gateway_timeout(self) -> None:
        create_response = self.client.post(
            "/api/projects",
            json={
                "project_name": "四会翡翠账号",
                "industry": "珠宝",
                "sub_industry": "翡翠",
                "product": "翡翠",
                "personal_intro": "在四会卖翡翠多年，为人靠谱",
                "target_audience": "喜欢翡翠，想买翡翠的人",
                "platforms": ["抖音"],
                "current_stage": "冷启动",
            },
        )
        project_id = create_response.json()["data"]["id"]
        topic_response = self.client.post(
            "/api/creation/topics/generate",
            json={"project_id": project_id, "platform": "抖音", "goal": "获客", "count": 1},
        )
        topic_id = topic_response.json()["data"]["topics"][0]["id"]
        calls = []
        gateway_response = LLMGatewayResponse(
            success=True,
            provider="test",
            model="test-model",
            content="",
            data={
                "title": "紫光灯看翡翠",
                "hook": "紫光灯一打，细节藏不住。",
                "script_content": "今天用60秒讲清楚这只翡翠手镯怎么看。",
                "shot_suggestions": ["拍手镯近景", "拍证书和卡尺"],
                "subtitle_points": ["先看自然光", "再看细节"],
                "conversion_script": "评论预算和用途。",
                "comment_guidance": "评论区发预算。",
                "private_message_guidance": "私信发图帮你看。",
            },
            usage={},
            latency_ms=1,
            generation_record_id=88,
        )

        def fake_generate(**kwargs):
            calls.append(kwargs["request"])
            return gateway_response

        with patch("app.services.script_service.LLMGateway") as gateway_class:
            gateway_class.return_value.generate.side_effect = fake_generate
            response = self.client.post(
                "/api/creation/scripts/generate",
                json={"project_id": project_id, "topic_id": topic_id, "temperature": 0.2},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(calls[0].max_tokens, 4000)
        self.assertLess(len(calls[0].user_prompt), 1800)


if __name__ == "__main__":
    unittest.main()
