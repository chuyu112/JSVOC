import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import auth_account, credit, generation_record, hot_copy, llm_channel, project, user  # noqa: F401


class HotCopyApiTest(unittest.TestCase):
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

    def register_user(self, username: str, email: str) -> int:
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
        return int(response.json()["data"]["user"]["id"])

    def create_project(self) -> int:
        response = self.client.post(
            "/api/projects",
            json={
                "project_name": "四会翡翠口播号",
                "industry": "珠宝",
                "sub_industry": "翡翠",
                "product": "翡翠手镯",
                "personal_intro": "在四会卖翡翠多年，擅长新手避坑。",
                "target_audience": "喜欢翡翠但怕踩坑的人",
                "platforms": ["抖音"],
                "current_stage": "冷启动",
            },
        )
        self.assertEqual(response.status_code, 201)
        return int(response.json()["data"]["id"])

    def create_material(self, **overrides) -> dict:
        payload = {
            "platform": "douyin",
            "title": "新手买翡翠别先问最低价",
            "original_script": "新手买翡翠，别一上来就问最低价。先看种水，再看纹裂，再看证书。",
            "source_url": "https://v.douyin.com/example/",
            "account_name": "四会源头老李",
            "metrics_json": {"likes": 12000, "comments": 600},
        }
        payload.update(overrides)
        response = self.client.post("/api/hot-copy/materials/manual", json=payload)
        self.assertEqual(response.status_code, 201)
        return response.json()["data"]

    def test_manual_material_requires_original_script(self) -> None:
        response = self.client.post(
            "/api/hot-copy/materials/manual",
            json={"platform": "douyin", "title": "爆款标题", "original_script": ""},
        )

        self.assertEqual(response.status_code, 422)
