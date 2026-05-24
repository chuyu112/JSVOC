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
from app.models import auth_account, credit, generation_record, project as project_model, user  # noqa: F401
from app.services import image_prompt_enhancement_service


class ImagePromptEnhancementTest(unittest.TestCase):
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
        self.project_id = self.create_project()

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def register_user(self) -> None:
        response = self.client.post(
            "/api/auth/register",
            json={
                "display_name": "Prompt User",
                "username": "promptuser",
                "email": "prompt@example.com",
                "password": "StrongPass123",
            },
        )
        self.assertEqual(response.status_code, 201)

    def create_project(self) -> int:
        response = self.client.post(
            "/api/projects",
            json={
                "project_name": "翡翠苹果",
                "industry": "珠宝",
                "sub_industry": "翡翠",
                "product": "满绿镶嵌戒面",
                "personal_intro": "苹果姐在四会做翡翠",
                "target_audience": "翡翠买家",
                "platforms": ["抖音"],
                "current_stage": "起号期",
            },
        )
        self.assertEqual(response.status_code, 201)
        return int(response.json()["data"]["id"])

    def test_extracts_project_name_and_person_terms_as_interference(self) -> None:
        with self.SessionLocal() as db:
            project = db.get(project_model.Project, self.project_id)
            terms = image_prompt_enhancement_service.extract_interference_terms(
                "为翡翠苹果和苹果姐生成一张产品图",
                project,
            )

        self.assertIn("翡翠苹果", terms)
        self.assertIn("苹果", terms)
        self.assertIn("苹果姐", terms)
        self.assertNotIn("满绿镶嵌戒面", terms)

    def test_enhance_prompt_filters_project_name_from_llm_output(self) -> None:
        fake_response = LLMGatewayResponse(
            success=True,
            provider="mock",
            model="mock-model",
            content="",
            data={
                "enhanced_prompt": "翡翠苹果的苹果造型吊坠，苹果姐手持满绿镶嵌戒面，干净留白，自然光，真实翡翠质感。",
                "subject": "满绿镶嵌戒面",
                "removed_terms": ["翡翠苹果", "苹果", "苹果姐"],
                "notes": ["过滤干扰词"],
            },
            usage={},
            latency_ms=1,
        )

        with patch("app.services.image_prompt_enhancement_service.LLMGateway.generate", return_value=fake_response):
            response = self.client.post(
                "/api/creation/images/enhance-prompt",
                json={
                    "project_id": self.project_id,
                    "prompt": "为翡翠苹果生成一张高级产品图",
                    "mode": "text",
                    "size": "1024x1024",
                    "quality": "high",
                },
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["subject"], "满绿镶嵌戒面")
        self.assertNotIn("翡翠苹果", data["enhanced_prompt"])
        self.assertNotIn("苹果姐", data["enhanced_prompt"])
        self.assertNotIn("苹果造型", data["enhanced_prompt"])
        self.assertIn("满绿镶嵌戒面", data["enhanced_prompt"])

    def test_enhance_prompt_forces_project_product_when_llm_is_generic(self) -> None:
        fake_response = LLMGatewayResponse(
            success=True,
            provider="mock",
            model="mock-model",
            content="",
            data={
                "enhanced_prompt": "以单件待展示商品为画面主体，正方形构图，柔和棚拍主光，浅灰背景，避免文字和无关物体。",
                "subject": "单件待展示商品",
                "removed_terms": [],
                "notes": [],
            },
            usage={},
            latency_ms=1,
        )

        with patch("app.services.image_prompt_enhancement_service.LLMGateway.generate", return_value=fake_response):
            response = self.client.post(
                "/api/creation/images/enhance-prompt",
                json={
                    "project_id": self.project_id,
                    "prompt": "生成一张产品图",
                    "mode": "text",
                },
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["subject"], "满绿镶嵌戒面")
        self.assertTrue(data["enhanced_prompt"].startswith("画面主体必须是满绿镶嵌戒面。"))


if __name__ == "__main__":
    unittest.main()
