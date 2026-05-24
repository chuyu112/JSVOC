import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import auth_account  # noqa: F401
from app.models import generation_record  # noqa: F401
from app.models import user  # noqa: F401


class VideoPromptEnhancementApiTest(unittest.TestCase):
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
        response = self.client.post(
            "/api/auth/register",
            json={
                "display_name": "Owner",
                "username": "owner",
                "email": "owner@example.com",
                "password": "StrongPass123",
            },
        )
        self.assertEqual(response.status_code, 201)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_mock_seedance_prompt_enhance_returns_direct_video_prompt(self) -> None:
        response = self.client.post(
            "/api/creation/videos/enhance-prompt",
            json={
                "prompt": "翡翠手镯在自然光下慢慢旋转，展示通透感",
                "material_hint": "jade",
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        enhanced_prompt = body["data"]["enhanced_prompt"]
        self.assertIn("翡翠手镯", enhanced_prompt)
        self.assertIn("camera", enhanced_prompt.lower())
        self.assertNotIn("module_name", enhanced_prompt)
        self.assertNotIn("mock provider 示例输出", enhanced_prompt)


if __name__ == "__main__":
    unittest.main()
