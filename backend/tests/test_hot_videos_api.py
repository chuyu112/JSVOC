import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.llm.llm_gateway import LLMGatewayResponse
from app.main import app
from app.models import auth_account, credit, generation_record, project, user  # noqa: F401


class HotVideosApiTest(unittest.TestCase):
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
        self.register_user()

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def register_user(self) -> None:
        response = self.client.post(
            "/api/auth/register",
            json={
                "display_name": "Research User",
                "username": "researcher",
                "email": "research@example.com",
                "password": "StrongPass123",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.user_id = response.json()["data"]["user"]["id"]

    def create_project(self) -> int:
        response = self.client.post(
            "/api/projects",
            json={
                "project_name": "翡翠苹果",
                "industry": "珠宝",
                "sub_industry": "翡翠",
                "product": "翡翠手镯",
                "personal_intro": "深耕翡翠多年",
                "target_audience": "喜欢翡翠但怕踩坑的人",
                "platforms": ["抖音"],
                "current_stage": "冷启动",
            },
        )
        self.assertEqual(response.status_code, 201)
        return response.json()["data"]["id"]

    def test_hot_video_search_uses_gateway_web_search(self) -> None:
        project_id = self.create_project()
        calls = []
        fake_response = LLMGatewayResponse(
            success=True,
            provider="openai_compatible",
            model="gpt-5.5",
            content="",
            data={
                "items": [
                    {
                        "title": "新手买翡翠别先问最低价",
                        "platform": "抖音",
                        "source_url": "https://example.com/video",
                        "metrics": {"likes": "1.2w"},
                        "why_trending": "反常识开头清晰",
                        "hook": "别先问最低价",
                        "structure": ["误区", "对比", "结论"],
                        "remake_angle": "用项目货品重写",
                        "rewrite_brief": "生成 60 秒避坑口播",
                    }
                ]
            },
            usage={"total_tokens": 88},
            sources=[{"url": "https://example.com/video", "title": "source"}],
            latency_ms=321,
            generation_record_id=66,
        )

        def fake_generate(**kwargs):
            calls.append(kwargs)
            return fake_response

        with patch("app.services.hot_video_service.LLMGateway.generate", side_effect=fake_generate):
            response = self.client.post(
                "/api/creation/hot-videos/search",
                json={
                    "project_id": project_id,
                    "platform": "抖音",
                    "keyword": "翡翠避坑",
                    "search_focus": "同赛道热门视频",
                    "count": 4,
                },
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["items"][0]["title"], "新手买翡翠别先问最低价")
        self.assertEqual(data["items"][0]["metrics"]["likes"], "1.2w")
        self.assertEqual(data["provider"], "openai_compatible")
        self.assertEqual(data["sources"][0]["url"], "https://example.com/video")
        self.assertEqual(calls[0]["project_id"], project_id)
        self.assertEqual(calls[0]["user_id"], self.user_id)
        self.assertEqual(calls[0]["request"].module_name, "hot_video_search")
        self.assertTrue(calls[0]["request"].web_search)
        self.assertIn("翡翠避坑", calls[0]["request"].user_prompt)


    def test_hot_video_search_can_use_opencli_results(self) -> None:
        project_id = self.create_project()
        calls = []
        fake_opencli_results = [
            {
                "title": "OpenCLI hot video",
                "source_url": "https://example.com/opencli",
                "source_title": "OpenCLI Source",
                "creator": "demo",
                "metrics": {"likes": "9000"},
                "summary": "A public search result.",
            }
        ]
        fake_response = LLMGatewayResponse(
            success=True,
            provider="openai_compatible",
            model="gpt-5.5",
            content="",
            data={
                "items": [
                    {
                        "title": "OpenCLI hot video",
                        "platform": "douyin",
                        "source_url": "https://example.com/opencli",
                        "remake_angle": "Use the same hook structure.",
                    }
                ]
            },
            usage={"total_tokens": 33},
            sources=[],
            latency_ms=123,
            generation_record_id=77,
        )

        def fake_generate(**kwargs):
            calls.append(kwargs)
            return fake_response

        with patch(
            "app.services.hot_video_service.opencli_search_service.search_hot_video_sources",
            return_value=(fake_opencli_results, 456),
        ), patch("app.services.hot_video_service.LLMGateway.generate", side_effect=fake_generate):
            response = self.client.post(
                "/api/creation/hot-videos/search",
                json={
                    "project_id": project_id,
                    "platform": "douyin",
                    "keyword": "jade",
                    "search_focus": "viral videos",
                    "count": 2,
                },
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["items"][0]["title"], "OpenCLI hot video")
        self.assertEqual(data["sources"][0]["url"], "https://example.com/opencli")
        self.assertEqual(data["usage"]["search_provider"], "opencli")
        self.assertEqual(data["usage"]["opencli_latency_ms"], 456)
        self.assertFalse(calls[0]["request"].web_search)
        self.assertIn("OpenCLI hot video", calls[0]["request"].user_prompt)

    def test_hot_video_search_opencli_provider_requires_command(self) -> None:
        project_id = self.create_project()

        with patch("app.services.hot_video_service.LLMGateway") as gateway_class:
            gateway = gateway_class.return_value
            gateway.settings.hot_video_search_provider = "opencli"
            gateway.settings.opencli_hot_video_search_command = ""
            response = self.client.post(
                "/api/creation/hot-videos/search",
                json={
                    "project_id": project_id,
                    "platform": "douyin",
                    "keyword": "jade",
                    "search_focus": "viral videos",
                    "count": 2,
                },
        )

        self.assertEqual(response.status_code, 502)
        self.assertIn("OPENCLI_HOT_VIDEO_SEARCH_COMMAND", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
