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
        self.assertEqual(created["purpose"], "chat")
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

    def test_active_channels_are_isolated_by_purpose(self) -> None:
        self.register("chuyu111")

        chat_response = self.client.post(
            "/api/admin/llm-channels",
            json={
                "name": "Chat",
                "purpose": "chat",
                "provider": "openai_compatible",
                "base_url": "https://chat.example.com/v1",
                "api_key": "chat-secret",
                "model": "chat-model",
                "is_active": True,
            },
        )
        self.assertEqual(chat_response.status_code, 201)
        chat_id = chat_response.json()["data"]["id"]

        image_response = self.client.post(
            "/api/admin/llm-channels",
            json={
                "name": "Image",
                "purpose": "image",
                "provider": "openai_compatible",
                "base_url": "https://image.example.com/v1",
                "api_key": "image-secret",
                "model": "image-model",
                "is_active": True,
            },
        )
        self.assertEqual(image_response.status_code, 201)
        image_id = image_response.json()["data"]["id"]

        second_chat_response = self.client.post(
            "/api/admin/llm-channels",
            json={
                "name": "Chat 2",
                "purpose": "chat",
                "provider": "mock",
                "base_url": "",
                "api_key": "",
                "model": "mock-model",
                "is_active": True,
            },
        )
        self.assertEqual(second_chat_response.status_code, 201)
        second_chat_id = second_chat_response.json()["data"]["id"]

        channels = self.client.get("/api/admin/llm-channels").json()["data"]
        active_by_id = {item["id"]: item["is_active"] for item in channels}
        purpose_by_id = {item["id"]: item["purpose"] for item in channels}

        self.assertFalse(active_by_id[chat_id])
        self.assertTrue(active_by_id[image_id])
        self.assertTrue(active_by_id[second_chat_id])
        self.assertEqual(purpose_by_id[image_id], "image")
        self.assertEqual(purpose_by_id[second_chat_id], "chat")

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

    def test_kakayiduo_chat_provider_uses_openai_compatible_transport(self) -> None:
        self.register("chuyu111")
        create_response = self.client.post(
            "/api/admin/llm-channels",
            json={
                "name": "kakayiduo-chat",
                "purpose": "chat",
                "provider": "kakayiduo-chat",
                "base_url": "http://43.173.105.8:8080/v1",
                "api_key": "kakayiduo-secret",
                "model": "gpt-5.5",
                "is_active": True,
            },
        )
        self.assertEqual(create_response.status_code, 201)
        created = create_response.json()["data"]
        self.assertEqual(created["provider"], "kakayiduo")
        channel_id = created["id"]

        fake_response = Mock()
        fake_response.raise_for_status.return_value = None
        fake_response.json.return_value = {
            "model": "gpt-5.5",
            "choices": [{"message": {"content": "{\"ok\": true}"}}],
            "usage": {"total_tokens": 3},
        }

        with patch("app.llm.llm_gateway._post_json", return_value=fake_response) as post_json:
            test_response = self.client.post(f"/api/admin/llm-channels/{channel_id}/test")

        self.assertEqual(test_response.status_code, 200)
        payload = test_response.json()["data"]
        self.assertTrue(payload["success"])
        self.assertEqual(payload["provider"], "kakayiduo")
        self.assertEqual(post_json.call_args.args[0], "http://43.173.105.8:8080/v1/chat/completions")
        self.assertEqual(post_json.call_args.kwargs["json"]["model"], "gpt-5.5")

    def test_legacy_provider_names_are_renamed(self) -> None:
        self.register("chuyu111")

        image_response = self.client.post(
            "/api/admin/llm-channels",
            json={
                "name": "Moyu Image",
                "purpose": "image",
                "provider": "moyu-pic",
                "base_url": "https://image.example.com/v1",
                "api_key": "image-secret",
                "model": "gpt-image-2",
                "is_active": True,
            },
        )
        self.assertEqual(image_response.status_code, 201)
        self.assertEqual(image_response.json()["data"]["provider"], "moyu_image")

        video_response = self.client.post(
            "/api/admin/llm-channels",
            json={
                "name": "Seedance Video",
                "purpose": "video",
                "provider": "ark-video",
                "base_url": "https://ark.example.com",
                "api_key": "video-secret",
                "model": "seedance-2.0",
                "is_active": True,
            },
        )
        self.assertEqual(video_response.status_code, 201)
        self.assertEqual(video_response.json()["data"]["provider"], "seedance_video")

        kakayiduo_response = self.client.post(
            "/api/admin/llm-channels",
            json={
                "name": "Kakayiduo Image",
                "purpose": "image",
                "provider": "kakayiduo-image",
                "base_url": "http://43.173.105.8:8080/v1",
                "api_key": "image-secret",
                "model": "gpt-image-2",
                "is_active": True,
            },
        )
        self.assertEqual(kakayiduo_response.status_code, 201)
        self.assertEqual(kakayiduo_response.json()["data"]["provider"], "kakayiduo")

    def test_image_channel_test_uses_image_generation_endpoint(self) -> None:
        self.register("chuyu111")
        create_response = self.client.post(
            "/api/admin/llm-channels",
            json={
                "name": "Image Runtime",
                "purpose": "image",
                "provider": "openai_compatible",
                "base_url": "https://image.example.com/v1",
                "api_key": "image-secret",
                "model": "gpt-image-2",
                "is_active": True,
            },
        )
        self.assertEqual(create_response.status_code, 201)
        channel_id = create_response.json()["data"]["id"]

        fake_response = Mock()
        fake_response.status_code = 200
        fake_response.raise_for_status.return_value = None
        fake_response.json.return_value = {
            "model": "gpt-image-2",
            "data": [{"b64_json": "aW1hZ2U="}],
            "usage": {"total_tokens": 1},
        }

        with (
            patch("app.llm.llm_gateway._post_json", side_effect=AssertionError("chat test should not run")),
            patch("app.services.image_generation_service.httpx.post", return_value=fake_response) as post_image,
        ):
            test_response = self.client.post(f"/api/admin/llm-channels/{channel_id}/test")

        self.assertEqual(test_response.status_code, 200)
        payload = test_response.json()["data"]
        self.assertTrue(payload["success"])
        self.assertEqual(payload["provider"], "openai_compatible")
        self.assertEqual(payload["model"], "gpt-image-2")
        call_kwargs = post_image.call_args.kwargs
        self.assertEqual(post_image.call_args.args[0], "https://image.example.com/v1/images/generations")
        self.assertEqual(call_kwargs["headers"]["Authorization"], "Bearer image-secret")
        self.assertEqual(call_kwargs["json"]["model"], "gpt-image-2")

    def test_kakayiduo_image_channel_test_uses_image_generation_endpoint(self) -> None:
        self.register("chuyu111")
        create_response = self.client.post(
            "/api/admin/llm-channels",
            json={
                "name": "kakayiduo-image",
                "purpose": "image",
                "provider": "kakayiduo",
                "base_url": "http://43.173.105.8:8080/v1",
                "api_key": "image-secret",
                "model": "gpt-image-2",
                "is_active": True,
            },
        )
        self.assertEqual(create_response.status_code, 201)
        created = create_response.json()["data"]
        self.assertEqual(created["provider"], "kakayiduo")
        channel_id = created["id"]

        fake_response = Mock()
        fake_response.status_code = 200
        fake_response.raise_for_status.return_value = None
        fake_response.json.return_value = {
            "model": "gpt-image-2",
            "data": [{"b64_json": "aW1hZ2U="}],
            "usage": {"total_tokens": 1},
        }

        with patch("app.services.image_generation_service.httpx.post", return_value=fake_response) as post_image:
            test_response = self.client.post(f"/api/admin/llm-channels/{channel_id}/test")

        self.assertEqual(test_response.status_code, 200)
        payload = test_response.json()["data"]
        self.assertTrue(payload["success"])
        self.assertEqual(payload["provider"], "kakayiduo")
        self.assertEqual(post_image.call_args.args[0], "http://43.173.105.8:8080/v1/images/generations")

    def test_video_channel_test_checks_config_without_submitting_task(self) -> None:
        self.register("chuyu111")
        create_response = self.client.post(
            "/api/admin/llm-channels",
            json={
                "name": "Video Runtime",
                "purpose": "video",
                "provider": "seedance-video",
                "base_url": "https://ark.example.com",
                "api_key": "video-secret",
                "model": "seedance-2.0",
                "is_active": True,
            },
        )
        self.assertEqual(create_response.status_code, 201)
        channel_id = create_response.json()["data"]["id"]

        with (
            patch("app.llm.llm_gateway._post_json", side_effect=AssertionError("chat test should not run")),
            patch(
                "app.services.video_generation_service.post_video_request_with_retry",
                side_effect=AssertionError("video test should not submit a task"),
            ),
        ):
            test_response = self.client.post(f"/api/admin/llm-channels/{channel_id}/test")

        self.assertEqual(test_response.status_code, 200)
        payload = test_response.json()["data"]
        self.assertTrue(payload["success"])
        self.assertEqual(payload["provider"], "seedance_video")
        self.assertEqual(payload["model"], "doubao-seedance-2-0-260128")


if __name__ == "__main__":
    unittest.main()
