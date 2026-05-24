import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app


class LLMChannelsApiTest(unittest.TestCase):
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

    def register(self, username: str) -> None:
        response = self.client.post(
            "/api/auth/register",
            json={
                "display_name": username,
                "username": username,
                "email": f"{username}@example.com",
                "password": "StrongPass123",
            },
        )
        self.assertEqual(response.status_code, 201)

    def test_non_admin_cannot_manage_llm_channels(self) -> None:
        self.register("normaluser")

        response = self.client.get("/api/admin/llm-channels")

        self.assertEqual(response.status_code, 403)

    def test_admin_can_manage_channels_without_exposing_api_key(self) -> None:
        self.register("chuyu111")

        empty_response = self.client.get("/api/admin/llm-channels")
        self.assertEqual(empty_response.status_code, 200)
        self.assertEqual(empty_response.json()["data"], [])

        create_response = self.client.post(
            "/api/admin/llm-channels",
            json={
                "name": "Primary LLM",
                "provider": "openai_compatible",
                "base_url": "https://llm.example.com/v1",
                "api_key": "first-secret",
                "model": "deepseek-v4-flash",
                "is_active": True,
            },
        )
        self.assertEqual(create_response.status_code, 201)
        created = create_response.json()["data"]
        self.assertEqual(created["name"], "Primary LLM")
        self.assertTrue(created["is_active"])
        self.assertTrue(created["has_api_key"])
        self.assertNotIn("api_key", created)

        channel_id = created["id"]
        update_response = self.client.patch(
            f"/api/admin/llm-channels/{channel_id}",
            json={
                "name": "Primary LLM Updated",
                "api_key": "",
                "model": "deepseek-v4-flash-2",
            },
        )
        self.assertEqual(update_response.status_code, 200)
        updated = update_response.json()["data"]
        self.assertEqual(updated["name"], "Primary LLM Updated")
        self.assertTrue(updated["has_api_key"])
        self.assertNotIn("api_key", updated)

        second_response = self.client.post(
            "/api/admin/llm-channels",
            json={
                "name": "Mock",
                "provider": "mock",
                "base_url": "",
                "api_key": "",
                "model": "mock-model",
                "is_active": True,
            },
        )
        self.assertEqual(second_response.status_code, 201)
        second_id = second_response.json()["data"]["id"]

        list_response = self.client.get("/api/admin/llm-channels")
        self.assertEqual(list_response.status_code, 200)
        channels = list_response.json()["data"]
        active_ids = [item["id"] for item in channels if item["is_active"]]
        self.assertEqual(active_ids, [second_id])

        activate_response = self.client.post(f"/api/admin/llm-channels/{channel_id}/activate")
        self.assertEqual(activate_response.status_code, 200)
        self.assertTrue(activate_response.json()["data"]["is_active"])

        delete_response = self.client.delete(f"/api/admin/llm-channels/{second_id}")
        self.assertEqual(delete_response.status_code, 200)

    def test_active_channel_overrides_env_settings_for_gateway_and_preserves_secret(self) -> None:
        self.register("chuyu111")
        create_response = self.client.post(
            "/api/admin/llm-channels",
            json={
                "name": "Runtime Channel",
                "provider": "openai_compatible",
                "base_url": "https://runtime.example.com/v1",
                "api_key": "runtime-secret",
                "model": "runtime-model",
                "is_active": True,
            },
        )
        self.assertEqual(create_response.status_code, 201)
        channel_id = create_response.json()["data"]["id"]

        preserve_response = self.client.patch(
            f"/api/admin/llm-channels/{channel_id}",
            json={"api_key": ""},
        )
        self.assertEqual(preserve_response.status_code, 200)

        fake_response = Mock()
        fake_response.raise_for_status.return_value = None
        fake_response.json.return_value = {
            "model": "runtime-model",
            "choices": [{"message": {"content": "{\"ok\": true}"}}],
            "usage": {"total_tokens": 3},
        }

        with patch("app.llm.llm_gateway._post_json", return_value=fake_response) as post_json:
            test_response = self.client.post(f"/api/admin/llm-channels/{channel_id}/test")

        self.assertEqual(test_response.status_code, 200)
        payload = test_response.json()["data"]
        self.assertTrue(payload["success"])
        self.assertEqual(payload["provider"], "openai_compatible")
        self.assertEqual(payload["model"], "runtime-model")
        call_args = post_json.call_args.args
        call_kwargs = post_json.call_args.kwargs
        self.assertEqual(call_args[0], "https://runtime.example.com/v1/chat/completions")
        self.assertEqual(call_kwargs["headers"]["Authorization"], "Bearer runtime-secret")
        self.assertEqual(call_kwargs["json"]["model"], "runtime-model")


if __name__ == "__main__":
    unittest.main()
