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
            LLM_BASE_URL="https://api.deepseek.com/chat/completions",
            LLM_API_KEY="test-key",
            LLM_MODEL="deepseek-v4-flash",
            LLM_TIMEOUT_SECONDS=2.5,
        )

        with patch("app.llm.llm_gateway._post_json", side_effect=fake_post):
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
        self.assertEqual(calls[0]["url"], "https://api.deepseek.com/chat/completions")
        self.assertEqual(calls[0]["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(calls[0]["json"]["model"], "deepseek-v4-flash")
        self.assertEqual(calls[0]["json"]["max_tokens"], 8000)
        self.assertNotIn("thinking", calls[0]["json"])
        self.assertNotIn("reasoning_effort", calls[0]["json"])
        self.assertEqual(calls[0]["timeout"], 2.5)
        record = self.db.scalar(select(GenerationRecord).where(GenerationRecord.id == result.generation_record_id))
        self.assertIsNotNone(record)
        self.assertEqual(record.module_name, "account_package")
        self.assertEqual(record.model_provider, "openai_compatible")
        self.assertEqual(record.model_name, "local-qwen")
        self.assertEqual(record.token_usage["total_tokens"], 12)
        self.assertIsInstance(record.latency_ms, int)

    def test_openai_compatible_uses_request_max_tokens_when_set(self) -> None:
        calls = []

        def fake_post(url, headers, json, timeout):
            calls.append(json)
            return httpx.Response(
                200,
                json={
                    "model": "local-qwen",
                    "choices": [{"message": {"content": '{"answer": "ok"}'}}],
                    "usage": {"total_tokens": 12},
                },
                request=httpx.Request("POST", url),
            )

        settings = Settings(
            LLM_PROVIDER="openai_compatible",
            LLM_BASE_URL="https://example.com/v1",
            LLM_API_KEY="test-key",
            LLM_MODEL="gpt-5.5",
        )

        with patch("app.llm.llm_gateway._post_json", side_effect=fake_post):
            result = LLMGateway(settings=settings).generate(
                db=self.db,
                request=LLMGatewayRequest(
                    module_name="strategy_bundle",
                    user_prompt="generate",
                    max_tokens=8000,
                ),
            )

        self.assertTrue(result.success)
        self.assertEqual(calls[0]["max_tokens"], 8000)

    def test_openai_compatible_web_search_uses_responses_api_and_sources(self) -> None:
        calls = []

        def fake_post(url, headers, json, timeout):
            calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
            return httpx.Response(
                200,
                json={
                    "model": "gpt-5",
                    "output_text": "阿森纳最新排名需要以英超官网为准。",
                    "output": [
                        {
                            "type": "web_search_call",
                            "action": {
                                "type": "search",
                                "queries": ["Arsenal Premier League table"],
                                "sources": [
                                    {
                                        "type": "url",
                                        "url": "https://www.premierleague.com/tables",
                                        "title": "Premier League Tables",
                                    }
                                ],
                            },
                        },
                        {
                            "type": "message",
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": "阿森纳最新排名需要以英超官网为准。",
                                    "annotations": [
                                        {
                                            "type": "url_citation",
                                            "url": "https://www.premierleague.com/tables",
                                            "title": "Premier League Tables",
                                        }
                                    ],
                                }
                            ],
                        },
                    ],
                    "usage": {"total_tokens": 32},
                },
                request=httpx.Request("POST", url),
            )

        settings = Settings(
            LLM_PROVIDER="openai_compatible",
            LLM_BASE_URL="https://api.openai.com/v1/chat/completions",
            LLM_API_KEY="test-key",
            LLM_MODEL="gpt-5",
            LLM_TIMEOUT_SECONDS=8,
        )

        with patch("app.llm.llm_gateway._post_json", side_effect=fake_post):
            result = LLMGateway(settings=settings).generate(
                db=self.db,
                request=LLMGatewayRequest(
                    module_name="ai_chat",
                    system_prompt="system",
                    user_prompt="查一下阿森纳排名",
                    web_search=True,
                    max_tokens=1200,
                ),
            )

        self.assertTrue(result.success)
        self.assertEqual(result.content, "阿森纳最新排名需要以英超官网为准。")
        self.assertEqual(result.sources[0]["url"], "https://www.premierleague.com/tables")
        self.assertEqual(calls[0]["url"], "https://api.openai.com/v1/responses")
        self.assertEqual(calls[0]["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(calls[0]["json"]["model"], "gpt-5")
        self.assertEqual(calls[0]["json"]["instructions"], "system")
        self.assertEqual(
            calls[0]["json"]["input"],
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "查一下阿森纳排名"},
                    ],
                }
            ],
        )
        self.assertNotIn("max_output_tokens", calls[0]["json"])
        self.assertEqual(calls[0]["json"]["tools"][0]["type"], "web_search")
        self.assertEqual(calls[0]["json"]["tool_choice"], "auto")
        self.assertIn("web_search_call.action.sources", calls[0]["json"]["include"])

    def test_openai_compatible_web_search_accepts_sse_responses_from_proxy(self) -> None:
        calls = []
        sse_body = "\n\n".join(
            [
                'event: response.created\n'
                'data: {"type":"response.created","response":{"id":"resp_1","status":"in_progress","output":[]}}',
                'event: response.output_text.done\n'
                'data: {"type":"response.output_text.done","text":"联网搜索结果摘要"}',
                'event: response.completed\n'
                'data: {"type":"response.completed","response":{"id":"resp_1","model":"gpt-5.5",'
                '"status":"completed","output":[{"type":"message","content":[{"type":"output_text",'
                '"text":"联网搜索结果摘要","annotations":[{"type":"url_citation",'
                '"url":"https://example.com/search","title":"Search Result"}]}]}],'
                '"usage":{"input_tokens":10,"output_tokens":5}}}',
                "data: [DONE]",
            ]
        )

        def fake_post(url, headers, json, timeout):
            calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
            return httpx.Response(
                200,
                text=sse_body,
                headers={"content-type": "text/event-stream"},
                request=httpx.Request("POST", url),
            )

        settings = Settings(
            LLM_PROVIDER="openai_compatible",
            LLM_BASE_URL="http://api.kakayiduo.cloud/v1",
            LLM_API_KEY="test-key",
            LLM_MODEL="gpt-5.5",
            LLM_TIMEOUT_SECONDS=8,
        )

        with patch("app.llm.llm_gateway._post_json", side_effect=fake_post):
            result = LLMGateway(settings=settings).generate(
                db=self.db,
                request=LLMGatewayRequest(
                    module_name="ai_chat",
                    system_prompt="system",
                    user_prompt="查一下今天的短视频热点",
                    web_search=True,
                    temperature=0.55,
                ),
            )

        self.assertTrue(result.success)
        self.assertEqual(result.content, "联网搜索结果摘要")
        self.assertEqual(result.sources[0]["url"], "https://example.com/search")
        self.assertEqual(result.usage["input_tokens"], 10)
        self.assertEqual(calls[0]["url"], "https://api.kakayiduo.cloud/v1/responses")
        self.assertNotIn("temperature", calls[0]["json"])

    def test_kakayiduo_web_search_preserves_configured_http_gateway_url(self) -> None:
        calls = []

        def fake_post(url, headers, json, timeout):
            calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
            return httpx.Response(
                200,
                json={"output_text": "ok", "output": [], "model": "gpt-5.5", "usage": {"total_tokens": 1}},
                request=httpx.Request("POST", url),
            )

        settings = Settings(
            LLM_PROVIDER="kakayiduo",
            LLM_BASE_URL="http://43.173.105.8:8080/v1",
            LLM_API_KEY="test-key",
            LLM_MODEL="gpt-5.5",
            LLM_TIMEOUT_SECONDS=8,
        )

        with patch("app.llm.llm_gateway._post_json", side_effect=fake_post):
            result = LLMGateway(settings=settings).generate(
                self.db,
                request=LLMGatewayRequest(
                    module_name="ai_chat",
                    user_prompt="search",
                    web_search=True,
                ),
            )

        self.assertTrue(result.success)
        self.assertEqual(calls[0]["url"], "http://43.173.105.8:8080/v1/responses")
        self.assertEqual(calls[0]["headers"]["Authorization"], "Bearer test-key")

    def test_dataeye_provider_uses_openai_compatible_transport_and_records_provider(self) -> None:
        calls = []

        def fake_post(url, headers, json, timeout):
            calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
            return httpx.Response(
                200,
                json={
                    "model": "dataeye-test-model",
                    "choices": [{"message": {"content": '{"answer": "ok"}'}}],
                    "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
                },
                request=httpx.Request("POST", url),
            )

        settings = Settings(
            LLM_PROVIDER="dataeye",
            LLM_BASE_URL="https://platform.shuyanai.com",
            LLM_API_KEY="test-key",
            LLM_MODEL="dataeye-test-model",
            LLM_TIMEOUT_SECONDS=4,
        )

        with patch("app.llm.llm_gateway._post_json", side_effect=fake_post):
            result = LLMGateway(settings=settings).generate(
                db=self.db,
                request=LLMGatewayRequest(
                    module_name="topics",
                    system_prompt="system",
                    user_prompt="user",
                ),
            )

        self.assertTrue(result.success)
        self.assertEqual(result.provider, "dataeye")
        self.assertEqual(result.model, "dataeye-test-model")
        self.assertEqual(result.data, {"answer": "ok"})
        self.assertEqual(calls[0]["url"], "https://platform.shuyanai.com/v1/chat/completions")
        self.assertEqual(calls[0]["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(calls[0]["json"]["model"], "dataeye-test-model")
        self.assertEqual(calls[0]["timeout"], 4)

        record = self.db.scalar(select(GenerationRecord).where(GenerationRecord.id == result.generation_record_id))
        self.assertIsNotNone(record)
        self.assertEqual(record.model_provider, "dataeye")
        self.assertEqual(record.model_name, "dataeye-test-model")
        self.assertEqual(record.token_usage["total_tokens"], 5)

    def test_moyu_provider_uses_openai_compatible_transport_and_strips_post_prefix(self) -> None:
        calls = []

        def fake_post(url, headers, json, timeout):
            calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
            return httpx.Response(
                200,
                json={
                    "model": "deepseek-v4-flash",
                    "choices": [{"message": {"content": '{"answer": "ok"}'}}],
                    "usage": {"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6},
                },
                request=httpx.Request("POST", url),
            )

        settings = Settings(
            LLM_PROVIDER="moyu",
            LLM_BASE_URL="POST https://www.moyu.info/v1/chat/completions",
            LLM_API_KEY="test-key",
            LLM_MODEL="deepseek-v4-flash",
            LLM_TIMEOUT_SECONDS=6,
        )

        with patch("app.llm.llm_gateway._post_json", side_effect=fake_post):
            result = LLMGateway(settings=settings).generate(
                db=self.db,
                request=LLMGatewayRequest(module_name="topics", user_prompt="user"),
            )

        self.assertTrue(result.success)
        self.assertEqual(result.provider, "moyu")
        self.assertEqual(result.model, "deepseek-v4-flash")
        self.assertEqual(result.data, {"answer": "ok"})
        self.assertEqual(calls[0]["url"], "https://www.moyu.info/v1/chat/completions")
        self.assertEqual(calls[0]["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(calls[0]["json"]["model"], "deepseek-v4-flash")
        self.assertEqual(calls[0]["timeout"], 6)

        record = self.db.scalar(select(GenerationRecord).where(GenerationRecord.id == result.generation_record_id))
        self.assertIsNotNone(record)
        self.assertEqual(record.model_provider, "moyu")
        self.assertEqual(record.model_name, "deepseek-v4-flash")
        self.assertEqual(record.token_usage["total_tokens"], 6)

    def test_openai_compatible_extracts_json_from_markdown_fence(self) -> None:
        calls = []

        def fake_post(url, headers, json, timeout):
            calls.append(json)
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
            LLM_BASE_URL="https://api.deepseek.com/chat/completions",
            LLM_MODEL="deepseek-v4-flash",
            LLM_TIMEOUT_SECONDS=5,
        )

        with patch("app.llm.llm_gateway._post_json", side_effect=fake_post):
            result = LLMGateway(settings=settings).generate(
                db=self.db,
                request=LLMGatewayRequest(module_name="topics", user_prompt="generate topics"),
            )

        self.assertTrue(result.success)
        self.assertEqual(result.data["topics"][0]["title"], "四会翡翠避坑")
        self.assertEqual(calls[0]["max_tokens"], 8000)
        self.assertNotIn("thinking", calls[0])
        self.assertNotIn("reasoning_effort", calls[0])

    def test_openai_compatible_routes_deepseek_account_package_to_v4_flash_without_thinking(self) -> None:
        calls = []

        def fake_post(url, headers, json, timeout):
            calls.append(json)
            return httpx.Response(
                200,
                json={
                    "model": "deepseek-v4-flash",
                    "choices": [{"message": {"content": '{"answer": "ok"}'}}],
                    "usage": {},
                },
                request=httpx.Request("POST", url),
            )

        settings = Settings(
            LLM_PROVIDER="openai_compatible",
            LLM_BASE_URL="https://api.deepseek.com/chat/completions",
            LLM_MODEL="deepseek-v4-flash",
            LLM_TIMEOUT_SECONDS=5,
        )

        with patch("app.llm.llm_gateway._post_json", side_effect=fake_post):
            result = LLMGateway(settings=settings).generate(
                db=self.db,
                request=LLMGatewayRequest(module_name="account_package", user_prompt="generate"),
            )

        self.assertTrue(result.success)
        self.assertEqual(calls[0]["model"], "deepseek-v4-flash")
        self.assertNotIn("thinking", calls[0])
        self.assertNotIn("reasoning_effort", calls[0])

    def test_openai_compatible_routes_deepseek_execution_plan_to_v4_flash_without_override(self) -> None:
        calls = []

        def fake_post(url, headers, json, timeout):
            calls.append(json)
            return httpx.Response(
                200,
                json={
                    "model": "deepseek-v4-flash",
                    "choices": [{"message": {"content": '{"answer": "ok"}'}}],
                    "usage": {},
                },
                request=httpx.Request("POST", url),
            )

        settings = Settings(
            LLM_PROVIDER="openai_compatible",
            LLM_BASE_URL="https://api.deepseek.com/chat/completions",
            LLM_MODEL="deepseek-v4-pro",
            EXECUTION_PLAN_MODEL="deepseek-v4-flash",
            LLM_TIMEOUT_SECONDS=5,
        )

        with patch("app.llm.llm_gateway._post_json", side_effect=fake_post):
            result = LLMGateway(settings=settings).generate(
                db=self.db,
                request=LLMGatewayRequest(module_name="execution_plan", user_prompt="generate"),
            )

        self.assertTrue(result.success)
        self.assertEqual(calls[0]["model"], "deepseek-v4-flash")
        self.assertNotIn("thinking", calls[0])
        self.assertNotIn("reasoning_effort", calls[0])

    def test_openai_compatible_routes_account_package_and_execution_plan_to_module_model_overrides(self) -> None:
        calls = []

        def fake_post(url, headers, json, timeout):
            calls.append(json)
            return httpx.Response(
                200,
                json={
                    "model": json["model"],
                    "choices": [{"message": {"content": '{"answer": "ok"}'}}],
                    "usage": {},
                },
                request=httpx.Request("POST", url),
            )

        settings = Settings(
            LLM_PROVIDER="moyu",
            LLM_BASE_URL="https://www.moyu.info/v1/chat/completions",
            LLM_MODEL="deepseek-v4-flash",
            ACCOUNT_PACKAGE_MODEL="gpt-5.5",
            EXECUTION_PLAN_MODEL="gpt-5.5",
            LLM_TIMEOUT_SECONDS=5,
        )

        with patch("app.llm.llm_gateway._post_json", side_effect=fake_post):
            for module_name in ["account_package", "execution_plan", "topics"]:
                result = LLMGateway(settings=settings).generate(
                    db=self.db,
                    request=LLMGatewayRequest(module_name=module_name, user_prompt="generate"),
                )
                self.assertTrue(result.success)

        self.assertEqual(calls[0]["model"], "gpt-5.5")
        self.assertNotIn("thinking", calls[0])
        self.assertNotIn("reasoning_effort", calls[0])
        self.assertEqual(calls[1]["model"], "gpt-5.5")
        self.assertNotIn("thinking", calls[1])
        self.assertNotIn("reasoning_effort", calls[1])
        self.assertEqual(calls[2]["model"], "deepseek-v4-flash")

    def test_gpt_api_alias_uses_openai_compatible_transport_and_falls_back_to_llm_model(self) -> None:
        calls = []

        def fake_post(url, headers, json, timeout):
            calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
            return httpx.Response(
                200,
                json={
                    "model": json["model"],
                    "choices": [{"message": {"content": '{"answer": "ok"}'}}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                },
                request=httpx.Request("POST", url),
            )

        settings = Settings(
            LLM_PROVIDER="gpt-api",
            LLM_BASE_URL="http://api.kakayiduo.cloud/v1",
            LLM_API_KEY="test-key",
            LLM_MODEL="gpt-5.4",
            ACCOUNT_PACKAGE_MODEL="",
            EXECUTION_PLAN_MODEL="",
            LLM_TIMEOUT_SECONDS=5,
        )

        with patch("app.llm.llm_gateway._post_json", side_effect=fake_post):
            result = LLMGateway(settings=settings).generate(
                db=self.db,
                request=LLMGatewayRequest(module_name="account_package", user_prompt="generate"),
            )

        self.assertTrue(result.success)
        self.assertEqual(result.provider, "openai_compatible")
        self.assertEqual(result.model, "gpt-5.4")
        self.assertEqual(calls[0]["url"], "http://api.kakayiduo.cloud/v1/chat/completions")
        self.assertEqual(calls[0]["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(calls[0]["json"]["model"], "gpt-5.4")
        self.assertNotIn("thinking", calls[0]["json"])
        self.assertNotIn("reasoning_effort", calls[0]["json"])

    def test_kakayiduo_provider_uses_configured_chat_endpoint_and_supported_models(self) -> None:
        calls = []

        def fake_post(url, headers, json, timeout):
            calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
            return httpx.Response(
                200,
                json={
                    "model": json["model"],
                    "choices": [{"message": {"content": '{"answer": "ok"}'}}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                },
                request=httpx.Request("POST", url),
            )

        settings = Settings(
            LLM_PROVIDER="kakayiduo",
            LLM_BASE_URL="http://43.173.105.8:8080/v1",
            LLM_API_KEY="test-key",
            LLM_MODEL="gpt-5.4-mini",
            ACCOUNT_PACKAGE_MODEL="deepseek-v4-flash",
            EXECUTION_PLAN_MODEL="deepseek-v4-flash",
            LLM_TIMEOUT_SECONDS=5,
        )

        with patch("app.llm.llm_gateway._post_json", side_effect=fake_post):
            result = LLMGateway(settings=settings).generate(
                db=self.db,
                request=LLMGatewayRequest(module_name="account_package", user_prompt="generate"),
            )

        self.assertTrue(result.success)
        self.assertEqual(result.provider, "kakayiduo")
        self.assertEqual(result.model, "gpt-5.4-mini")
        self.assertEqual(calls[0]["url"], "http://43.173.105.8:8080/v1/chat/completions")
        self.assertEqual(calls[0]["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(calls[0]["json"]["model"], "gpt-5.4-mini")

    def test_openai_compatible_allows_deepseek_account_package_model_override(self) -> None:
        calls = []

        def fake_post(url, headers, json, timeout):
            calls.append(json)
            return httpx.Response(
                200,
                json={
                    "model": "deepseek-v4-flash",
                    "choices": [{"message": {"content": '{"answer": "ok"}'}}],
                    "usage": {},
                },
                request=httpx.Request("POST", url),
            )

        settings = Settings(
            LLM_PROVIDER="openai_compatible",
            LLM_BASE_URL="https://api.deepseek.com/chat/completions",
            LLM_MODEL="deepseek-v4-pro",
            DEEPSEEK_ACCOUNT_PACKAGE_MODEL="deepseek-v4-flash",
            LLM_TIMEOUT_SECONDS=5,
        )

        with patch("app.llm.llm_gateway._post_json", side_effect=fake_post):
            result = LLMGateway(settings=settings).generate(
                db=self.db,
                request=LLMGatewayRequest(module_name="account_package", user_prompt="generate"),
            )

        self.assertTrue(result.success)
        self.assertEqual(calls[0]["model"], "deepseek-v4-flash")
        self.assertNotIn("thinking", calls[0])
        self.assertNotIn("reasoning_effort", calls[0])

    def test_openai_compatible_routes_deepseek_topics_to_v4_flash_without_thinking(self) -> None:
        calls = []

        def fake_post(url, headers, json, timeout):
            calls.append(json)
            return httpx.Response(
                200,
                json={
                    "model": "deepseek-v4-flash",
                    "choices": [{"message": {"content": '{"topics": []}'}}],
                    "usage": {},
                },
                request=httpx.Request("POST", url),
            )

        settings = Settings(
            LLM_PROVIDER="openai_compatible",
            LLM_BASE_URL="https://api.deepseek.com/chat/completions",
            LLM_MODEL="deepseek-v4-pro",
            LLM_TIMEOUT_SECONDS=5,
        )

        with patch("app.llm.llm_gateway._post_json", side_effect=fake_post):
            result = LLMGateway(settings=settings).generate(
                db=self.db,
                request=LLMGatewayRequest(module_name="topics", user_prompt="generate"),
            )

        self.assertTrue(result.success)
        self.assertEqual(calls[0]["model"], "deepseek-v4-flash")
        self.assertNotIn("thinking", calls[0])
        self.assertNotIn("reasoning_effort", calls[0])

    def test_openai_compatible_repairs_unescaped_quotes_inside_json_strings(self) -> None:
        def fake_post(url, headers, json, timeout):
            return httpx.Response(
                200,
                json={
                    "model": "glm-4-airx",
                    "choices": [
                        {
                            "message": {
                                "content": (
                                    "```json\n"
                                    "{\n"
                                    '  "cycle": 30,\n'
                                    '  "weekly_plan": [\n'
                                    '    {"week": 1, "goal": "start", "key_tasks": ["发起"翡翠知识问答"互动活动"]}\n'
                                    "  ],\n"
                                    '  "daily_plan": [\n'
                                    '    {"day": 1, "task": "拍摄", "topic": "四会翡翠", "shooting_task": "市场实拍", "review_metrics": ["完播率"]}\n'
                                    "  ]\n"
                                    "}\n"
                                    "```"
                                )
                            }
                        }
                    ],
                    "usage": {},
                },
                request=httpx.Request("POST", url),
            )

        settings = Settings(
            LLM_PROVIDER="openai_compatible",
            LLM_BASE_URL="http://127.0.0.1:11434/v1",
            LLM_MODEL="glm-4-airx",
            LLM_TIMEOUT_SECONDS=5,
        )

        with patch("app.llm.llm_gateway._post_json", side_effect=fake_post):
            result = LLMGateway(settings=settings).generate(
                db=self.db,
                request=LLMGatewayRequest(
                    module_name="execution_plan",
                    user_prompt="generate execution plan",
                ),
            )

        self.assertTrue(result.success)
        self.assertEqual(
            result.data["weekly_plan"][0]["key_tasks"][0],
            '发起"翡翠知识问答"互动活动',
        )
        self.assertEqual(result.data["daily_plan"][0]["topic"], "四会翡翠")

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

        with patch("app.llm.llm_gateway._post_json", side_effect=fake_post):
            result = LLMGateway(settings=settings).generate(
                db=self.db,
                request=LLMGatewayRequest(module_name="script", user_prompt="generate script"),
            )

        self.assertFalse(result.success)
        self.assertEqual(result.provider, "openai_compatible")
        self.assertIn("500", result.error or "")
        self.assertIsNotNone(result.generation_record_id)

    def test_anthropic_compatible_sends_messages_request_and_records_usage(self) -> None:
        calls = []

        def fake_post(url, headers, json, timeout):
            calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
            return httpx.Response(
                200,
                json={
                    "model": "deepseek-v4-flash",
                    "content": [{"type": "text", "text": '{"answer": "ok"}'}],
                    "usage": {"input_tokens": 11, "output_tokens": 7},
                },
                request=httpx.Request("POST", url),
            )

        settings = Settings(
            LLM_PROVIDER="anthropic_compatible",
            LLM_BASE_URL="https://api.deepseek.com/anthropic",
            LLM_API_KEY="test-key",
            LLM_MODEL="deepseek-v4-flash",
            LLM_TIMEOUT_SECONDS=3,
        )

        with patch("app.llm.llm_gateway._post_json", side_effect=fake_post):
            result = LLMGateway(settings=settings).generate(
                db=self.db,
                request=LLMGatewayRequest(
                    module_name="topics",
                    system_prompt="system",
                    user_prompt="user",
                    temperature=0.3,
                ),
                project_id=123,
            )

        self.assertTrue(result.success)
        self.assertEqual(result.provider, "anthropic_compatible")
        self.assertEqual(result.model, "deepseek-v4-flash")
        self.assertEqual(result.data, {"answer": "ok"})
        self.assertEqual(result.usage["total_tokens"], 18)
        self.assertEqual(calls[0]["url"], "https://api.deepseek.com/anthropic/v1/messages")
        self.assertEqual(calls[0]["headers"]["x-api-key"], "test-key")
        self.assertEqual(calls[0]["headers"]["anthropic-version"], "2023-06-01")
        self.assertEqual(calls[0]["json"]["model"], "deepseek-v4-flash")
        self.assertEqual(calls[0]["json"]["system"], "system")
        self.assertEqual(calls[0]["json"]["messages"][0]["content"], "user")
        self.assertEqual(calls[0]["json"]["temperature"], 0.3)
        self.assertEqual(calls[0]["json"]["max_tokens"], 8000)
        self.assertEqual(calls[0]["json"]["thinking"], {"type": "disabled"})
        self.assertNotIn("output_config", calls[0]["json"])
        self.assertEqual(calls[0]["timeout"], 3)

        record = self.db.scalar(select(GenerationRecord).where(GenerationRecord.id == result.generation_record_id))
        self.assertIsNotNone(record)
        self.assertEqual(record.model_provider, "anthropic_compatible")
        self.assertEqual(record.model_name, "deepseek-v4-flash")
        self.assertEqual(record.token_usage["total_tokens"], 18)

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

        with patch("app.llm.llm_gateway._post_json", side_effect=fake_post):
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
