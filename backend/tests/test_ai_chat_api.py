import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.llm.llm_gateway import LLMGatewayResponse
from app.main import app
from app.models import auth_account, credit, generation_record, user  # noqa: F401
from app.models.credit import CreditTransaction
from app.models.generation_record import GenerationRecord
from app.services import credit_service


class AIChatApiTest(unittest.TestCase):
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
                "display_name": "Chat User",
                "username": "chatuser",
                "email": "chat@example.com",
                "password": "StrongPass123",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.user_id = response.json()["data"]["user"]["id"]

    def test_ai_chat_uses_gateway_and_returns_reply(self) -> None:
        calls = []
        fake_response = LLMGatewayResponse(
            success=True,
            provider="openai_compatible",
            model="gpt-5.5",
            content="先把账号定位收紧，再拆选题和脚本。",
            data={"text": "unused"},
            usage={"total_tokens": 42},
            latency_ms=123,
            generation_record_id=77,
            sources=[{"url": "https://example.com/source", "title": "Example Source"}],
        )

        def fake_generate(**kwargs):
            calls.append(kwargs)
            return fake_response

        with patch("app.services.ai_chat_service.LLMGateway.generate", side_effect=fake_generate):
            response = self.client.post(
                "/api/ai-chat",
                json={
                    "message": "我的账号应该先优化什么？",
                    "conversation_id": "conv-main",
                    "conversation_title": "账号优化",
                    "history": [
                        {"role": "user", "content": "我是做翡翠的"},
                        {"role": "assistant", "content": "先确认目标客户"},
                    ],
                    "web_search": True,
                },
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        data = body["data"]
        self.assertEqual(data["reply"], "先把账号定位收紧，再拆选题和脚本。")
        self.assertEqual(data["provider"], "openai_compatible")
        self.assertEqual(data["model"], "gpt-5.5")
        self.assertEqual(data["usage"]["total_tokens"], 42)
        self.assertEqual(data["latency_ms"], 123)
        self.assertEqual(data["generation_record_id"], 77)
        self.assertEqual(data["sources"][0]["url"], "https://example.com/source")
        self.assertEqual(data["conversation_id"], "conv-main")
        self.assertEqual(data["conversation_title"], "账号优化")

        self.assertEqual(calls[0]["user_id"], self.user_id)
        self.assertIsNone(calls[0]["project_id"])
        self.assertEqual(calls[0]["request"].module_name, "ai_chat")
        self.assertTrue(calls[0]["request"].web_search)
        self.assertEqual(calls[0]["request"].max_tokens, 1800)
        self.assertEqual(calls[0]["request"].metadata["message"], "我的账号应该先优化什么？")
        self.assertEqual(calls[0]["request"].metadata["conversation_id"], "conv-main")
        self.assertEqual(calls[0]["request"].metadata["conversation_title"], "账号优化")
        self.assertIn("我是做翡翠的", calls[0]["request"].user_prompt)
        self.assertIn("我的账号应该先优化什么？", calls[0]["request"].user_prompt)

    def test_ai_chat_rejects_empty_message(self) -> None:
        response = self.client.post("/api/ai-chat", json={"message": "   "})

        self.assertEqual(response.status_code, 422)

    def test_ai_chat_charges_minimum_credit_cost(self) -> None:
        fake_response = LLMGatewayResponse(
            success=True,
            provider="mock",
            model="mock-model",
            content="reply",
            usage={"total_tokens": 42},
            latency_ms=10,
            generation_record_id=88,
        )

        with patch("app.services.ai_chat_service.LLMGateway.generate", return_value=fake_response):
            response = self.client.post("/api/ai-chat", json={"message": "hello"})

        self.assertEqual(response.status_code, 200)
        balance_response = self.client.get("/api/credits/balance")
        self.assertEqual(balance_response.json()["data"]["balance"], 1990)

        with self.SessionLocal() as db:
            transaction = db.query(CreditTransaction).filter_by(reason="ai_chat_generation").one()
            self.assertEqual(transaction.amount, -10)
            self.assertEqual(transaction.reference_type, "generation_record")
            self.assertEqual(transaction.reference_id, 88)
            self.assertEqual(transaction.transaction_metadata["total_tokens"], 42)

    def test_ai_chat_requires_minimum_credit_balance_before_calling_gateway(self) -> None:
        with self.SessionLocal() as db:
            account = credit_service.get_or_create_account(db, self.user_id)
            account.balance = 9
            db.commit()

        with patch("app.services.ai_chat_service.LLMGateway.generate") as generate:
            response = self.client.post("/api/ai-chat", json={"message": "hello"})

        self.assertEqual(response.status_code, 402)
        generate.assert_not_called()

    def test_ai_chat_history_returns_saved_turns_for_current_user(self) -> None:
        base_time = datetime(2026, 1, 1, 12, 0, 0)
        with self.SessionLocal() as db:
            db.add_all(
                [
                    GenerationRecord(
                        user_id=self.user_id,
                        project_id=None,
                        module_name="ai_chat",
                        input_data={
                            "user_prompt": "以下是当前聊天上下文，请基于上下文回答最后一个问题。\n\n历史对话：\n无\n\n当前问题：\n第一条问题",
                            "metadata": {"history_count": 0, "web_search": False},
                        },
                        output_data={"success": True, "content": "第一条回复", "data": {}, "error": None},
                        model_provider="mock",
                        model_name="mock-model",
                        prompt_version="ai-chat-v1",
                        token_usage={},
                        latency_ms=11,
                        created_at=base_time,
                    ),
                    GenerationRecord(
                        user_id=self.user_id,
                        project_id=None,
                        module_name="ai_chat",
                        input_data={
                            "user_prompt": "prompt with fallback",
                            "metadata": {"message": "第二条问题", "history_count": 2, "web_search": True},
                        },
                        output_data={
                            "success": True,
                            "content": '{"reply": "第二条回复"}',
                            "data": {"reply": "第二条回复"},
                            "error": None,
                        },
                        model_provider="openai_compatible",
                        model_name="gpt-test",
                        prompt_version="ai-chat-v1",
                        token_usage={},
                        latency_ms=22,
                        created_at=base_time + timedelta(minutes=1),
                    ),
                    GenerationRecord(
                        user_id=self.user_id + 100,
                        project_id=None,
                        module_name="ai_chat",
                        input_data={"metadata": {"message": "别人的问题"}},
                        output_data={"success": True, "content": "别人的回复", "data": {}, "error": None},
                        model_provider="mock",
                        model_name="mock-model",
                        token_usage={},
                        created_at=base_time + timedelta(minutes=2),
                    ),
                    GenerationRecord(
                        user_id=self.user_id,
                        project_id=None,
                        module_name="topics",
                        input_data={"metadata": {"message": "不是聊天"}},
                        output_data={"success": True, "content": "不是聊天回复", "data": {}, "error": None},
                        model_provider="mock",
                        model_name="mock-model",
                        token_usage={},
                        created_at=base_time + timedelta(minutes=3),
                    ),
                ]
            )
            db.commit()

        response = self.client.get("/api/ai-chat/history?limit=10")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual([item["user_message"] for item in body["data"]], ["第一条问题", "第二条问题"])
        self.assertEqual([item["assistant_message"] for item in body["data"]], ["第一条回复", "第二条回复"])
        self.assertEqual(body["data"][1]["provider"], "openai_compatible")
        self.assertEqual(body["data"][1]["model"], "gpt-test")
        self.assertEqual(body["data"][1]["web_search"], True)

    def test_ai_chat_conversations_group_topics_and_load_selected_history(self) -> None:
        base_time = datetime(2026, 1, 1, 12, 0, 0)
        with self.SessionLocal() as db:
            db.add_all(
                [
                    GenerationRecord(
                        user_id=self.user_id,
                        project_id=None,
                        module_name="ai_chat",
                        input_data={
                            "metadata": {
                                "message": "账号定位怎么做？",
                                "conversation_id": "conv-a",
                                "conversation_title": "账号定位",
                            }
                        },
                        output_data={"success": True, "content": "先收紧人群", "data": {}, "error": None},
                        model_provider="mock",
                        model_name="mock-model",
                        token_usage={},
                        created_at=base_time,
                    ),
                    GenerationRecord(
                        user_id=self.user_id,
                        project_id=None,
                        module_name="ai_chat",
                        input_data={
                            "metadata": {
                                "message": "继续拆选题",
                                "conversation_id": "conv-a",
                                "conversation_title": "账号定位",
                            }
                        },
                        output_data={"success": True, "content": "按痛点拆", "data": {}, "error": None},
                        model_provider="mock",
                        model_name="mock-model",
                        token_usage={},
                        created_at=base_time + timedelta(minutes=1),
                    ),
                    GenerationRecord(
                        user_id=self.user_id,
                        project_id=None,
                        module_name="ai_chat",
                        input_data={
                            "metadata": {
                                "message": "生图提示词怎么写？",
                                "conversation_id": "conv-b",
                                "conversation_title": "生图提示词",
                            }
                        },
                        output_data={"success": True, "content": "先写主体和材质", "data": {}, "error": None},
                        model_provider="mock",
                        model_name="mock-model",
                        token_usage={},
                        created_at=base_time + timedelta(minutes=2),
                    ),
                    GenerationRecord(
                        user_id=self.user_id,
                        project_id=None,
                        module_name="ai_chat",
                        input_data={
                            "user_prompt": "以下是当前聊天上下文，请基于上下文回答最后一个问题。\n\n历史对话：\n无\n\n当前问题：\n旧聊天问题",
                            "metadata": {"message": "旧聊天问题"},
                        },
                        output_data={"success": True, "content": "旧聊天回复", "data": {}, "error": None},
                        model_provider="mock",
                        model_name="mock-model",
                        token_usage={},
                        created_at=base_time + timedelta(minutes=3),
                    ),
                ]
            )
            db.commit()

        conversations_response = self.client.get("/api/ai-chat/conversations?limit=10")

        self.assertEqual(conversations_response.status_code, 200)
        conversations = conversations_response.json()["data"]
        self.assertEqual([item["conversation_id"] for item in conversations], ["legacy", "conv-b", "conv-a"])
        self.assertEqual(conversations[0]["title"], "历史聊天")
        self.assertEqual(conversations[1]["title"], "生图提示词")
        self.assertEqual(conversations[2]["turn_count"], 2)
        self.assertEqual(conversations[2]["last_user_message"], "继续拆选题")

        history_response = self.client.get("/api/ai-chat/conversations/conv-a/history?limit=10")

        self.assertEqual(history_response.status_code, 200)
        history = history_response.json()["data"]
        self.assertEqual([item["user_message"] for item in history], ["账号定位怎么做？", "继续拆选题"])
        self.assertEqual([item["assistant_message"] for item in history], ["先收紧人群", "按痛点拆"])


if __name__ == "__main__":
    unittest.main()
