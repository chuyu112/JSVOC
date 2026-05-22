import unittest
from unittest.mock import patch

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.db.base import Base
from app.llm.llm_gateway import LLMGateway, LLMGatewayRequest
from app.models import account_strategy_context  # noqa: F401
from app.models import generation_record  # noqa: F401
from app.models import project  # noqa: F401
from app.models import script  # noqa: F401
from app.models import topic  # noqa: F401
from app.models.generation_record import GenerationRecord


class OpenAICompatibleGatewayTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_openai_compatible_sends_request_to_base_url_and_records_usage(self) -> None:
        calls = []

        def fake_post(url, headers, json, timeout):
            calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
            return httpx.Response(
                200,
                json={
                    "model": "local-qwen",
                    "choices": [{"message": {"content": '{"answer": "ok"}'}}],
                    "usage": {"prompt_tokens": 7, "completion_tokens": 5, "total_tokens": 12},
                },
                request=httpx.Request("POST", url),
            )

        settings = Settings(
            LLM_PROVIDER="openai_compatible",
            LLM_BASE_URL="http://127.0.0.1:11434/v1",
            LLM_API_KEY="test-key",
            LLM_MODEL="qwen-local",
            LLM_TIMEOUT_SECONDS=2.5,
        )

        with patch("app.llm.llm_gateway.httpx.post", side_effect=fake_post):
            result = LLMGateway(settings=settings).generate(
                db=self.db,
                request=LLMGatewayRequest(
                    module_name="account_package",
                    system_prompt="system",
                    user_prompt="user",
                ),
                project_id=123,
            )

        self.assertTrue(result.success)
        self.assertEqual(result.provider, "openai_compatible")
        self.assertEqual(result.model, "local-qwen")
        self.assertEqual(result.data, {"answer": "ok"})
        self.assertEqual(result.usage["total_tokens"], 12)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["url"], "http://127.0.0.1:11434/v1/chat/completions")
        self.assertEqual(calls[0]["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(calls[0]["json"]["model"], "qwen-local")
        self.assertEqual(calls[0]["timeout"], 2.5)

        record = self.db.scalar(select(GenerationRecord).where(GenerationRecord.id == result.generation_record_id))
        self.assertIsNotNone(record)
        self.assertEqual(record.module_name, "account_package")
        self.assertEqual(record.model_provider, "openai_compatible")
        self.assertEqual(record.model_name, "local-qwen")
        self.assertEqual(record.token_usage["total_tokens"], 12)
        self.assertIsInstance(record.latency_ms, int)

    def test_openai_compatible_extracts_json_from_markdown_fence(self) -> None:
        def fake_post(url, headers, json, timeout):
            return httpx.Response(
                200,
                json={
                    "model": "local-qwen",
                    "choices": [
                        {
                            "message": {
                                "content": '```json\n{"topics": [{"title": "四会翡翠避坑"}]}\n```'
                            }
                        }
                    ],
                    "usage": {},
                },
                request=httpx.Request("POST", url),
            )

        settings = Settings(
            LLM_PROVIDER="openai_compatible",
            LLM_BASE_URL="http://127.0.0.1:11434/v1/chat/completions",
            LLM_MODEL="qwen-local",
            LLM_TIMEOUT_SECONDS=5,
        )

        with patch("app.llm.llm_gateway.httpx.post", side_effect=fake_post):
            result = LLMGateway(settings=settings).generate(
                db=self.db,
                request=LLMGatewayRequest(module_name="topics", user_prompt="generate topics"),
            )

        self.assertTrue(result.success)
        self.assertEqual(result.data["topics"][0]["title"], "四会翡翠避坑")

    def test_openai_compatible_returns_error_response_for_http_failure(self) -> None:
        def fake_post(url, headers, json, timeout):
            return httpx.Response(
                500,
                json={"error": {"message": "local model unavailable"}},
                request=httpx.Request("POST", url),
            )

        settings = Settings(
            LLM_PROVIDER="openai_compatible",
            LLM_BASE_URL="http://127.0.0.1:11434/v1",
            LLM_MODEL="qwen-local",
            LLM_TIMEOUT_SECONDS=5,
        )

        with patch("app.llm.llm_gateway.httpx.post", side_effect=fake_post):
            result = LLMGateway(settings=settings).generate(
                db=self.db,
                request=LLMGatewayRequest(module_name="script", user_prompt="generate script"),
            )

        self.assertFalse(result.success)
        self.assertEqual(result.provider, "openai_compatible")
        self.assertIn("500", result.error or "")
        self.assertIsNotNone(result.generation_record_id)

    def test_openai_compatible_supports_all_mvp_modules_through_same_gateway(self) -> None:
        calls = []

        def fake_post(url, headers, json, timeout):
            calls.append(json["messages"][1]["content"])
            return httpx.Response(
                200,
                json={
                    "model": "local-qwen",
                    "choices": [{"message": {"content": '{"ok": true}'}}],
                    "usage": {"total_tokens": 3},
                },
                request=httpx.Request("POST", url),
            )

        settings = Settings(
            LLM_PROVIDER="openai_compatible",
            LLM_BASE_URL="http://127.0.0.1:11434/v1",
            LLM_MODEL="qwen-local",
            LLM_TIMEOUT_SECONDS=5,
        )
        gateway = LLMGateway(settings=settings)

        with patch("app.llm.llm_gateway.httpx.post", side_effect=fake_post):
            for module_name in ["account_package", "execution_plan", "topics", "script"]:
                result = gateway.generate(
                    db=self.db,
                    request=LLMGatewayRequest(
                        module_name=module_name,
                        user_prompt=f"generate {module_name}",
                    ),
                )
                self.assertTrue(result.success)
                self.assertEqual(result.provider, "openai_compatible")
                self.assertEqual(result.model, "local-qwen")
                self.assertIsNotNone(result.generation_record_id)

        records = self.db.scalars(select(GenerationRecord)).all()
        self.assertEqual(
            [record.module_name for record in records],
            ["account_package", "execution_plan", "topics", "script"],
        )
        self.assertEqual(len(calls), 4)


if __name__ == "__main__":
    unittest.main()
