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
from app.models import account_strategy_context  # noqa: F401
from app.models.account_strategy_context import AccountStrategyContext
from app.models.credit import CreditTransaction
from app.models import generation_record  # noqa: F401
from app.models.generation_record import GenerationRecord
from app.models import project  # noqa: F401
from app.services import credit_service


def account_package_payload(label: str) -> dict[str, object]:
    return {
        "account_positioning": f"{label} positioning",
        "persona": f"{label} persona",
        "target_user_profile": {"segment": f"{label} buyers"},
        "account_names": [f"{label} account name"],
        "bios": {"douyin": f"{label} bio"},
        "content_columns": [f"{label} content column"],
        "trust_design": [f"{label} trust point"],
        "conversion_path": [f"{label} conversion path"],
        "platform_strategies": {"douyin": f"{label} platform strategy"},
    }


def execution_plan_payload(label: str) -> dict[str, object]:
    return {
        "cycle": "30 days",
        "weekly_plan": [
            {
                "week": 1,
                "goal": f"{label} weekly goal",
                "focus": f"{label} focus",
                "key_tasks": [f"{label} weekly task"],
            }
        ],
        "daily_plan": [
            {
                "day": 1,
                "task": f"{label} daily task",
                "topic": f"{label} topic",
                "shooting_task": f"{label} shooting task",
                "review_metrics": [f"{label} metric"],
            }
        ],
    }


class AccountPackageApiTest(unittest.TestCase):
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

    def create_project(self) -> int:
        response = self.client.post(
            "/api/projects",
            json={
                "project_name": "jade account",
                "industry": "jewelry",
                "sub_industry": "jade",
                "product": "jade bracelet",
                "personal_intro": "20 years jade seller",
                "target_audience": "city gift buyers",
                "platforms": ["douyin", "shipinhao"],
                "current_stage": "stable",
            },
        )
        return response.json()["data"]["id"]

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

    def test_legacy_strategy_routes_are_removed(self) -> None:
        project_id = self.create_project()

        account_response = self.client.post(
            "/api/strategy/account-package/generate",
            json={"project_id": project_id},
        )
        execution_response = self.client.post(
            "/api/strategy/execution-plan/generate",
            json={"project_id": project_id},
        )

        self.assertEqual(account_response.status_code, 404)
        self.assertEqual(execution_response.status_code, 404)

    def test_bundle_missing_project_returns_not_found(self) -> None:
        response = self.client.post(
            "/api/strategy/account-package-execution-plan/generate",
            json={"project_id": 999},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "项目不存在")

    def test_bundle_gateway_failure_does_not_create_account_strategy_context(self) -> None:
        project_id = self.create_project()
        failed_result = LLMGatewayResponse(
            success=False,
            provider="test",
            model="test-model",
            content="",
            data={},
            usage={},
            latency_ms=1,
            error="provider unavailable",
        )

        with patch("app.api.strategy_bundle.LLMGateway") as gateway_class:
            gateway_class.return_value.generate.return_value = failed_result
            response = self.client.post(
                "/api/strategy/account-package-execution-plan/generate",
                json={"project_id": project_id},
            )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["detail"], "provider unavailable")

        with self.SessionLocal() as db:
            contexts = db.query(AccountStrategyContext).all()
            self.assertEqual(contexts, [])

    def test_bundle_generation_returns_account_package_and_execution_plan_in_one_call(self) -> None:
        project_id = self.create_project()
        calls = []
        gateway_result = LLMGatewayResponse(
            success=True,
            provider="test",
            model="test-model",
            content="",
            data={
                "account_package": account_package_payload("bundle"),
                "execution_plan": execution_plan_payload("bundle"),
            },
            usage={"total_tokens": 123},
            latency_ms=10,
            generation_record_id=201,
        )

        def fake_generate(**kwargs):
            calls.append(kwargs["request"])
            return gateway_result

        with patch("app.api.strategy_bundle.LLMGateway") as gateway_class:
            gateway_class.return_value.generate.side_effect = fake_generate
            response = self.client.post(
                "/api/strategy/account-package-execution-plan/generate",
                json={"project_id": project_id, "cycle": "30 days", "daily_time": "2 hours"},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].module_name, "strategy_bundle")
        self.assertEqual(calls[0].max_tokens, 8000)
        self.assertIn("account_package", body["data"])
        self.assertIn("execution_plan", body["data"])
        self.assertEqual(body["data"]["provider"], "test")
        self.assertEqual(body["data"]["model"], "test-model")
        self.assertEqual(
            body["data"]["account_package"]["account_positioning"],
            "bundle positioning",
        )
        self.assertEqual(
            body["data"]["execution_plan"]["weekly_plan"][0]["goal"],
            "bundle weekly goal",
        )

        with self.SessionLocal() as db:
            contexts = db.query(AccountStrategyContext).all()
            self.assertEqual(len(contexts), 1)
            self.assertEqual(contexts[0].account_positioning, "bundle positioning")

    def test_bundle_generation_charges_by_token_usage_rounded_to_ten_credit_unit(self) -> None:
        project_id = self.create_project()
        gateway_result = LLMGatewayResponse(
            success=True,
            provider="test",
            model="test-model",
            content="",
            data={
                "account_package": account_package_payload("priced"),
                "execution_plan": execution_plan_payload("priced"),
            },
            usage={"total_tokens": 1_234_567},
            latency_ms=10,
            generation_record_id=301,
        )

        with patch("app.api.strategy_bundle.LLMGateway") as gateway_class:
            gateway_class.return_value.generate.return_value = gateway_result
            response = self.client.post(
                "/api/strategy/account-package-execution-plan/generate",
                json={"project_id": project_id, "cycle": "30 days", "daily_time": "2 hours"},
            )

        self.assertEqual(response.status_code, 200)
        balance_response = self.client.get("/api/credits/balance")
        self.assertEqual(balance_response.json()["data"]["balance"], 1870)

        with self.SessionLocal() as db:
            transaction = db.query(CreditTransaction).filter_by(reason="strategy_bundle_generation").one()
            self.assertEqual(transaction.amount, -130)
            self.assertEqual(transaction.reference_type, "generation_record")
            self.assertEqual(transaction.reference_id, 301)
            self.assertEqual(transaction.transaction_metadata["module"], "strategy_bundle")
            self.assertEqual(transaction.transaction_metadata["project_id"], project_id)
            self.assertEqual(transaction.transaction_metadata["total_tokens"], 1_234_567)

    def test_latest_bundle_does_not_require_credit_balance(self) -> None:
        project_id = self.create_project()
        gateway_result = LLMGatewayResponse(
            success=True,
            provider="test",
            model="test-model",
            content="",
            data={
                "account_package": account_package_payload("latest"),
                "execution_plan": execution_plan_payload("latest"),
            },
            usage={"total_tokens": 1},
            latency_ms=10,
            generation_record_id=302,
        )
        with patch("app.api.strategy_bundle.LLMGateway") as gateway_class:
            gateway_class.return_value.generate.return_value = gateway_result
            create_response = self.client.post(
                "/api/strategy/account-package-execution-plan/generate",
                json={"project_id": project_id},
            )
        self.assertEqual(create_response.status_code, 200)

        with self.SessionLocal() as db:
            account = credit_service.get_or_create_account(db, 1)
            account.balance = 0
            db.commit()

        latest_response = self.client.get(
            f"/api/strategy/account-package-execution-plan/projects/{project_id}/latest"
        )

        self.assertEqual(latest_response.status_code, 200)
        self.assertEqual(latest_response.json()["data"]["account_positioning"], "latest positioning")

    def test_second_bundle_generation_replaces_previous_strategy_context_and_record(self) -> None:
        project_id = self.create_project()
        self.client.post(
            "/api/strategy/account-package-execution-plan/generate",
            json={"project_id": project_id},
        )
        response = self.client.post(
            "/api/strategy/account-package-execution-plan/generate",
            json={"project_id": project_id},
        )

        self.assertEqual(response.status_code, 200)
        with self.SessionLocal() as db:
            contexts = db.query(AccountStrategyContext).all()
            records = db.query(GenerationRecord).filter(GenerationRecord.module_name == "strategy_bundle").all()

        self.assertEqual(len(contexts), 1)
        self.assertEqual(len(records), 1)


if __name__ == "__main__":
    unittest.main()
