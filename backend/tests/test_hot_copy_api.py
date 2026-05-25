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

    def test_create_and_list_manual_materials(self) -> None:
        material = self.create_material()

        response = self.client.get("/api/hot-copy/materials")

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data[0]["id"], material["id"])
        self.assertEqual(data[0]["platform"], "douyin")
        self.assertEqual(data[0]["source_type"], "manual")

    def test_analyze_material_records_generation_history(self) -> None:
        material = self.create_material()

        response = self.client.post(f"/api/hot-copy/materials/{material['id']}/analyze")

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertIn("hook", data["analysis"])
        self.assertIsInstance(data["generation_record_id"], int)
        records = self.client.get("/api/generation-records?module_name=hot_copy_analysis").json()["data"]
        self.assertEqual(records[0]["id"], data["generation_record_id"])
        self.assertTrue(records[0]["output_data"]["success"])

    def test_rewrite_material_records_generation_history(self) -> None:
        project_id = self.create_project()
        material = self.create_material(project_id=project_id)
        analyze = self.client.post(f"/api/hot-copy/materials/{material['id']}/analyze")
        self.assertEqual(analyze.status_code, 200)

        response = self.client.post(
            f"/api/hot-copy/materials/{material['id']}/rewrite",
            json={
                "project_id": project_id,
                "rewrite_mode": "medium",
                "duration": "60s",
                "conversion_goal": "私信获客",
                "product": "翡翠手镯",
                "target_customer": "怕买贵的新手",
                "account_persona": "四会源头选品顾问",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertIn("script", data["output"])
        self.assertIsInstance(data["generation_record_id"], int)
        records = self.client.get("/api/generation-records?module_name=hot_copy_rewrite").json()["data"]
        self.assertEqual(records[0]["id"], data["generation_record_id"])
        self.assertTrue(records[0]["output_data"]["success"])
