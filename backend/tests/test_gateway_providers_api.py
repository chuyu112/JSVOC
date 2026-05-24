import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import account_strategy_context  # noqa: F401
from app.models import gateway_provider  # noqa: F401
from app.models import generation_record  # noqa: F401
from app.models import project  # noqa: F401
from app.models import script  # noqa: F401
from app.models import topic  # noqa: F401


class GatewayProvidersAdminApiTest(unittest.TestCase):
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
        self.headers = {"X-Admin-Token": get_settings().admin_api_key}

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_admin_token_is_required(self) -> None:
        response = self.client.get("/api/admin/gateway-providers")

        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_list_update_and_select_default_provider(self) -> None:
        first_response = self.client.post(
            "/api/admin/gateway-providers",
            headers=self.headers,
            json={
                "capability": "chat",
                "name": "Local Qwen",
                "provider": "openai_compatible",
                "base_url": "http://127.0.0.1:11434/v1",
                "api_key": "secret-token-123456",
                "model": "qwen-local",
                "is_enabled": True,
                "is_default": True,
                "config": {"timeout_seconds": 30},
            },
        )
        self.assertEqual(first_response.status_code, 201)
        first_provider = first_response.json()["data"]
        self.assertTrue(first_provider["is_default"])
        self.assertTrue(first_provider["has_api_key"])
        self.assertNotIn("secret-token-123456", str(first_provider))

        second_response = self.client.post(
            "/api/admin/gateway-providers",
            headers=self.headers,
            json={
                "capability": "chat",
                "name": "Backup Mock",
                "provider": "mock",
                "model": "mock-model",
                "is_enabled": True,
                "is_default": True,
                "config": {},
            },
        )
        self.assertEqual(second_response.status_code, 201)
        second_provider = second_response.json()["data"]

        list_response = self.client.get(
            "/api/admin/gateway-providers?capability=chat",
            headers=self.headers,
        )
        self.assertEqual(list_response.status_code, 200)
        providers = list_response.json()["data"]
        self.assertEqual(len(providers), 2)
        self.assertEqual(
            [provider["id"] for provider in providers if provider["is_default"]],
            [second_provider["id"]],
        )

        default_response = self.client.post(
            f"/api/admin/gateway-providers/{first_provider['id']}/set-default",
            headers=self.headers,
        )
        self.assertEqual(default_response.status_code, 200)
        self.assertTrue(default_response.json()["data"]["is_default"])

        update_response = self.client.put(
            f"/api/admin/gateway-providers/{first_provider['id']}",
            headers=self.headers,
            json={"name": "Local Qwen Updated", "config": {"timeout_seconds": 10}},
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["data"]["name"], "Local Qwen Updated")
        self.assertEqual(update_response.json()["data"]["config"]["timeout_seconds"], 10)


if __name__ == "__main__":
    unittest.main()
