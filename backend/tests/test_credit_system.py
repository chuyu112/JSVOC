import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import credit, generation_task, project, user  # noqa: F401
from app.services import credit_service


class CreditSystemTest(unittest.TestCase):
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
                "display_name": "Credit User",
                "username": "credituser",
                "email": "credit@example.com",
                "password": "StrongPass123",
            },
        )
        self.assertEqual(response.status_code, 201)

    def set_user_balance(self, balance: int) -> None:
        with self.SessionLocal() as db:
            account = credit_service.get_or_create_account(db, 1)
            account.balance = balance
            db.commit()

    def test_credit_balance_and_package_endpoints(self) -> None:
        balance_response = self.client.get("/api/credits/balance")
        self.assertEqual(balance_response.status_code, 200)
        self.assertEqual(balance_response.json()["data"]["balance"], 2000)

        packages_response = self.client.get("/api/credits/packages")
        self.assertEqual(packages_response.status_code, 200)
        self.assertEqual(packages_response.json()["data"][0]["credits"], 10000)
        self.assertEqual(packages_response.json()["data"][0]["price_yuan"], 100)

    def test_async_image_generation_charges_queued_task(self) -> None:
        with patch("app.api.image_generation.run_image_generation_task", return_value=None):
            response = self.client.post(
                "/api/creation/images/generate/async",
                json={"prompt": "jade pendant product photo", "n": 2, "size": "1024x1536"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["credit_cost"], 200)

        balance_response = self.client.get("/api/credits/balance")
        self.assertEqual(balance_response.json()["data"]["balance"], 1800)

        with self.SessionLocal() as db:
            task = db.get(generation_task.GenerationTask, response.json()["data"]["task_id"])
            self.assertIsNotNone(task)
            self.assertEqual(task.credit_cost, 200)
            self.assertIsNotNone(task.credit_transaction_id)

    def test_insufficient_credits_blocks_generation(self) -> None:
        self.set_user_balance(10)
        response = self.client.post(
            "/api/creation/images/generate/async",
            json={"prompt": "jade pendant product photo", "n": 1, "size": "1024x1536"},
        )

        self.assertEqual(response.status_code, 402)
        self.assertIn("积分不足", response.json()["detail"])

    def test_video_generation_cost_uses_yuan_to_credit_rounding(self) -> None:
        cost = credit_service.video_generation_cost(
            {
                "model": "doubao-seedance-2-0-fast-260128",
                "resolution": "480p",
                "duration_mode": "fixed",
                "duration_seconds": 7,
                "count": 1,
            }
        )

        self.assertEqual(cost, 270)

    def test_ai_chat_cost_charges_minimum_for_small_token_usage(self) -> None:
        cost = credit_service.ai_chat_generation_cost({"total_tokens": 42})

        self.assertEqual(cost, 10)

    def test_ai_chat_cost_uses_one_hundred_credits_per_million_tokens(self) -> None:
        cost = credit_service.ai_chat_generation_cost({"total_tokens": 1_234_567})

        self.assertEqual(cost, 124)

    def test_topic_generation_cost_rounds_up_to_ten_credit_unit(self) -> None:
        cost = credit_service.topic_generation_cost({"total_tokens": 1_234_567})

        self.assertEqual(cost, 130)

    def test_image_generation_cost_is_fixed_per_request(self) -> None:
        self.assertEqual(credit_service.image_generation_cost(1, mode="generate"), 200)
        self.assertEqual(credit_service.image_generation_cost(10, mode="generate"), 200)
        self.assertEqual(credit_service.image_generation_cost(10, mode="edit"), 200)

    def test_seedance_2_fast_480p_15s_costs_5_6_yuan(self) -> None:
        cost = credit_service.video_generation_cost(
            {
                "model": "doubao-seedance-2-0-fast-260128",
                "resolution": "480p",
                "duration_mode": "seconds",
                "duration_seconds": 15,
                "count": 1,
            }
        )

        self.assertEqual(cost, 560)

    def test_seedance_2_fast_720p_15s_costs_12_yuan(self) -> None:
        cost = credit_service.video_generation_cost(
            {
                "model": "doubao-seedance-2-0-fast-260128",
                "resolution": "720p",
                "duration_mode": "seconds",
                "duration_seconds": 15,
                "count": 1,
            }
        )

        self.assertEqual(cost, 1200)

    def test_seedance_2_fast_rejects_1080p(self) -> None:
        with self.assertRaisesRegex(ValueError, "does not support 1080p"):
            credit_service.video_generation_cost(
                {
                    "model": "doubao-seedance-2-0-fast-260128",
                    "resolution": "1080p",
                    "duration_mode": "seconds",
                    "duration_seconds": 15,
                    "count": 1,
                }
            )

    def test_seedance_2_standard_15s_costs_by_resolution(self) -> None:
        cases = [
            ("480p", 700),
            ("720p", 1500),
            ("1080p", 3700),
        ]
        for resolution, expected_cost in cases:
            with self.subTest(resolution=resolution):
                cost = credit_service.video_generation_cost(
                    {
                        "model": "doubao-seedance-2-0-260128",
                        "resolution": resolution,
                        "duration_mode": "seconds",
                        "duration_seconds": 15,
                        "count": 1,
                    }
                )
                self.assertEqual(cost, expected_cost)

    def test_failed_generation_task_refunds_once(self) -> None:
        with patch("app.api.image_generation.run_image_generation_task", return_value=None):
            response = self.client.post(
                "/api/creation/images/generate/async",
                json={"prompt": "jade pendant product photo", "n": 1, "size": "1024x1536"},
            )
        task_id = response.json()["data"]["task_id"]

        with self.SessionLocal() as db:
            credit_service.refund_generation_task_credits(db, task_id, reason="test_failure")
            credit_service.refund_generation_task_credits(db, task_id, reason="test_failure_again")
            self.assertEqual(credit_service.get_balance(db, 1), 2000)


if __name__ == "__main__":
    unittest.main()
