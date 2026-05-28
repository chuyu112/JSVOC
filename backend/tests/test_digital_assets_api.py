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
from app.models import auth_account  # noqa: F401
from app.models import digital_asset  # noqa: F401
from app.models import generation_record  # noqa: F401
from app.models import project  # noqa: F401
from app.models import script  # noqa: F401
from app.models import topic  # noqa: F401
from app.models import user  # noqa: F401
from app.services import digital_asset_service


class DigitalAssetsApiTest(unittest.TestCase):
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

    def create_script_asset(self, client: TestClient | None = None) -> tuple[int, int]:
        client = client or self.client
        project_response = client.post(
            "/api/projects",
            json={
                "project_name": "jade project",
                "industry": "jewelry",
                "sub_industry": "jade",
                "product": "jade bracelet",
                "personal_intro": "seller",
                "target_audience": "buyers",
                "platforms": ["douyin"],
                "current_stage": "cold_start",
            },
        )
        project_id = project_response.json()["data"]["id"]

        topic_response = client.post(
            "/api/creation/topics/generate",
            json={"project_id": project_id, "platform": "douyin", "goal": "lead_generation", "count": 1},
        )
        topic_id = topic_response.json()["data"]["topics"][0]["id"]

        script_response = client.post(
            "/api/creation/scripts/generate",
            json={"project_id": project_id, "topic_id": topic_id},
        )
        self.assertEqual(script_response.status_code, 200)
        return project_id, script_response.json()["data"]["script"]["id"]

    def test_lists_script_assets_for_current_user(self) -> None:
        project_id, _script_id = self.create_script_asset()

        response = self.client.get("/api/digital-assets")

        self.assertEqual(response.status_code, 200)
        assets = response.json()["data"]
        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0]["asset_type"], "script")
        self.assertEqual(assets[0]["source_project_id"], project_id)
        self.assertEqual(assets[0]["project_snapshot"]["project_name"], "jade project")
        self.assertTrue(assets[0]["preview_text"])

    def test_deleting_project_reassigns_script_asset_to_account_and_preserves_source_metadata(self) -> None:
        project_id, _script_id = self.create_script_asset()

        delete_response = self.client.delete(f"/api/projects/{project_id}")
        self.assertEqual(delete_response.status_code, 200)

        assets_response = self.client.get("/api/digital-assets")
        self.assertEqual(assets_response.status_code, 200)
        assets = assets_response.json()["data"]
        self.assertEqual(len(assets), 1)
        self.assertIsNone(assets[0]["source_project_id"])
        self.assertEqual(assets[0]["project_snapshot"]["scope"], "account")
        self.assertEqual(assets[0]["project_snapshot"]["project_name"], "账户资产")
        self.assertEqual(assets[0]["asset_metadata"]["source_project"]["project_id"], project_id)
        self.assertEqual(assets[0]["asset_metadata"]["source_project"]["project_name"], "jade project")

    def test_digital_assets_are_scoped_to_current_user(self) -> None:
        self.create_script_asset(self.client)

        other_client = TestClient(app)
        self.register_user(other_client, "other", "other@example.com")
        self.create_script_asset(other_client)

        owner_assets = self.client.get("/api/digital-assets")
        other_assets = other_client.get("/api/digital-assets")

        self.assertEqual(owner_assets.status_code, 200)
        self.assertEqual(other_assets.status_code, 200)
        self.assertEqual(len(owner_assets.json()["data"]), 1)
        self.assertEqual(len(other_assets.json()["data"]), 1)
        self.assertNotEqual(owner_assets.json()["data"][0]["id"], other_assets.json()["data"][0]["id"])

    def test_account_scoped_assets_have_account_snapshot_without_project(self) -> None:
        with self.SessionLocal() as db:
            digital_asset_service.create_image_asset(
                db,
                user_id=1,
                project=None,
                prompt="account image",
                generation_record_id=None,
                oss_object_key="users/1/account/images/test.png",
                mime_type="image/png",
                file_size=128,
                asset_metadata={"provider": "test"},
            )

        response = self.client.get("/api/digital-assets")

        self.assertEqual(response.status_code, 200)
        assets = response.json()["data"]
        self.assertEqual(len(assets), 1)
        self.assertIsNone(assets[0]["source_project_id"])
        self.assertEqual(assets[0]["project_snapshot"]["scope"], "account")
        self.assertEqual(assets[0]["project_snapshot"]["project_name"], "账户资产")
        self.assertEqual(assets[0]["content_text"], "account image")
        self.assertEqual(assets[0]["asset_metadata"]["prompt"], "account image")


if __name__ == "__main__":
    unittest.main()
