import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.llm.llm_gateway import LLMGatewayResponse
from app.main import app
from app.models import account_strategy_context  # noqa: F401
from app.models import generation_record  # noqa: F401
from app.models import project  # noqa: F401
from app.models import topic  # noqa: F401
from app.models.credit import CreditTransaction
from app.models.generation_record import GenerationRecord


class TopicsApiTest(unittest.TestCase):
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

    def test_mock_provider_generates_and_saves_10_topics(self) -> None:
        create_response = self.client.post(
            "/api/projects",
            json={
                "project_name": "四会翡翠账号",
                "industry": "珠宝",
                "sub_industry": "翡翠",
                "product": "翡翠",
                "personal_intro": "在四会卖翡翠多年，为人靠谱",
                "target_audience": "喜欢翡翠，想买翡翠的人",
                "platforms": ["抖音", "视频号", "快手", "小红书"],
                "current_stage": "冷启动",
            },
        )
        project_id = create_response.json()["data"]["id"]

        response = self.client.post(
            "/api/creation/topics/generate",
            json={"project_id": project_id, "platform": "抖音", "goal": "获客", "count": 10},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        topics = body["data"]["topics"]
        self.assertEqual(len(topics), 10)

        for item in topics:
            self.assertIsInstance(item["id"], int)
            self.assertTrue(item["title"])
            self.assertEqual(item["platform"], "抖音")
            self.assertTrue(item["content_type"])
            self.assertEqual(item["goal"], "获客")
            self.assertTrue(item["topic_data"]["user_pain_point"])
            self.assertTrue(item["topic_data"]["hook"])
            self.assertTrue(item["topic_data"]["shooting_suggestion"])
            self.assertTrue(item["topic_data"]["conversion_method"])
            self.assertGreaterEqual(item["score"], 80)

        with self.SessionLocal() as db:
            topic_count = db.execute(
                text("select count(*) from topics where project_id = :project_id"),
                {"project_id": project_id},
            ).scalar_one()
            records = db.scalars(
                select(GenerationRecord).where(
                    GenerationRecord.project_id == project_id,
                    GenerationRecord.module_name == "topics",
                )
            ).all()

        self.assertEqual(topic_count, 10)
        self.assertEqual(len(records), 1)

    def test_generate_topics_rejects_more_than_10_per_request(self) -> None:
        create_response = self.client.post(
            "/api/projects",
            json={
                "project_name": "四会翡翠账号",
                "industry": "珠宝",
                "sub_industry": "翡翠",
                "product": "翡翠",
                "personal_intro": "在四会卖翡翠多年，为人靠谱",
                "target_audience": "喜欢翡翠，想买翡翠的人",
                "platforms": ["抖音"],
                "current_stage": "冷启动",
            },
        )
        project_id = create_response.json()["data"]["id"]

        response = self.client.post(
            "/api/creation/topics/generate",
            json={"project_id": project_id, "platform": "抖音", "goal": "获客", "count": 11},
        )

        self.assertEqual(response.status_code, 422)

    def test_generate_topics_records_client_target_count_metadata(self) -> None:
        create_response = self.client.post(
            "/api/projects",
            json={
                "project_name": "topic metadata test",
                "industry": "jewelry",
                "sub_industry": "jade",
                "product": "jade bracelet",
                "personal_intro": "seller",
                "target_audience": "buyers",
                "platforms": ["douyin"],
                "current_stage": "cold_start",
            },
        )
        project_id = create_response.json()["data"]["id"]

        response = self.client.post(
            "/api/creation/topics/generate",
            json={
                "project_id": project_id,
                "platform": "douyin",
                "goal": "lead_generation",
                "count": 3,
                "generation_target_count": 30,
            },
        )

        self.assertEqual(response.status_code, 200)
        with self.SessionLocal() as db:
            record = db.scalars(
                select(GenerationRecord).where(
                    GenerationRecord.project_id == project_id,
                    GenerationRecord.module_name == "topics",
                )
            ).one()

        self.assertEqual(record.input_data["metadata"]["count"], 3)
        self.assertEqual(record.input_data["metadata"]["generation_target_count"], 30)

    def test_generate_topics_charges_by_token_usage(self) -> None:
        create_response = self.client.post(
            "/api/projects",
            json={
                "project_name": "topic credit test",
                "industry": "jewelry",
                "sub_industry": "jade",
                "product": "jade bracelet",
                "personal_intro": "seller",
                "target_audience": "buyers",
                "platforms": ["douyin"],
                "current_stage": "cold_start",
            },
        )
        project_id = create_response.json()["data"]["id"]
        gateway_response = LLMGatewayResponse(
            success=True,
            provider="test",
            model="test-model",
            content="",
            data={
                "topics": [
                    {
                        "title": "token priced topic",
                        "content_type": "education",
                        "platform": "douyin",
                        "goal": "lead_generation",
                        "user_pain_point": "unknown quality",
                        "hook": "look here first",
                        "shooting_suggestion": "show detail",
                        "conversion_method": "comment budget",
                        "score": 90,
                    }
                ]
            },
            usage={"total_tokens": 1_234_567},
            latency_ms=1,
            generation_record_id=201,
        )

        with patch("app.services.topic_service.LLMGateway") as gateway_class:
            gateway_class.return_value.generate.return_value = gateway_response
            response = self.client.post(
                "/api/creation/topics/generate",
                json={"project_id": project_id, "platform": "douyin", "goal": "lead_generation", "count": 1},
            )

        self.assertEqual(response.status_code, 200)
        balance_response = self.client.get("/api/credits/balance")
        self.assertEqual(balance_response.json()["data"]["balance"], 1870)

        with self.SessionLocal() as db:
            transaction = db.query(CreditTransaction).filter_by(reason="topic_generation").one()
            self.assertEqual(transaction.amount, -130)
            self.assertEqual(transaction.reference_type, "generation_record")
            self.assertEqual(transaction.reference_id, 201)
            self.assertEqual(transaction.transaction_metadata["total_tokens"], 1_234_567)

    def test_generate_topics_batch_charges_by_token_usage(self) -> None:
        create_response = self.client.post(
            "/api/projects",
            json={
                "project_name": "topic batch credit test",
                "industry": "jewelry",
                "sub_industry": "jade",
                "product": "jade bracelet",
                "personal_intro": "seller",
                "target_audience": "buyers",
                "platforms": ["douyin"],
                "current_stage": "cold_start",
            },
        )
        project_id = create_response.json()["data"]["id"]
        topic_payload = {
            "id": 1,
            "project_id": project_id,
            "title": "batch token priced topic",
            "content_type": "education",
            "platform": "douyin",
            "goal": "lead_generation",
            "selling_point": "",
            "score": 90,
            "is_favorite": False,
            "topic_data": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        with patch("app.api.topics.topic_service.generate_topics_batch") as generate_batch:
            generate_batch.return_value = {
                "topics": [topic_payload],
                "generated_count": 1,
                "target_count": 1,
                "provider": "test",
                "model": "test-model",
                "latency_ms": 1,
                "usage": {"total_tokens": 25_000},
            }
            response = self.client.post(
                "/api/creation/topics/generate-batch",
                json={"project_id": project_id, "platform": "douyin", "goal": "lead_generation", "target_count": 1},
            )

        self.assertEqual(response.status_code, 200)
        balance_response = self.client.get("/api/credits/balance")
        self.assertEqual(balance_response.json()["data"]["balance"], 1990)

        with self.SessionLocal() as db:
            transaction = db.query(CreditTransaction).filter_by(reason="topic_batch_generation").one()
            self.assertEqual(transaction.amount, -10)
            self.assertEqual(transaction.reference_type, "topic_batch")
            self.assertEqual(transaction.transaction_metadata["total_tokens"], 25_000)

    def test_generate_topics_accepts_nested_topics_from_model_output(self) -> None:
        create_response = self.client.post(
            "/api/projects",
            json={
                "project_name": "四会翡翠账号",
                "industry": "珠宝",
                "sub_industry": "翡翠",
                "product": "翡翠手镯",
                "personal_intro": "在四会卖翡翠多年",
                "target_audience": "想买翡翠但怕踩坑的人",
                "platforms": ["抖音"],
                "current_stage": "冷启动",
            },
        )
        project_id = create_response.json()["data"]["id"]

        gateway_response = LLMGatewayResponse(
            success=True,
            provider="test",
            model="test-model",
            content="",
            data={
                "data": {
                    "topics": [
                        {
                            "title": "新手买翡翠先看这三个细节",
                            "content_type": "避坑科普",
                            "platform": "抖音",
                            "goal": "获客",
                            "user_pain_point": "怕买贵、怕买到处理货",
                            "hook": "新手买翡翠，别一上来就问最低价。",
                            "shooting_suggestion": "真人出镜，拿两只手镯对比种水和瑕疵。",
                            "conversion_method": "评论预算和用途，私信发图帮忙判断。",
                            "score": 92,
                        }
                    ]
                }
            },
            usage={},
            latency_ms=1,
        )

        with patch("app.services.topic_service.LLMGateway") as gateway_class:
            gateway_class.return_value.generate.return_value = gateway_response
            response = self.client.post(
                "/api/creation/topics/generate",
                json={
                    "project_id": project_id,
                    "platform": "抖音",
                    "goal": "获客",
                    "count": 10,
                },
            )

        self.assertEqual(response.status_code, 200)
        topics = response.json()["data"]["topics"]
        self.assertEqual(len(topics), 1)
        self.assertEqual(topics[0]["title"], "新手买翡翠先看这三个细节")
        self.assertEqual(topics[0]["topic_data"]["hook"], "新手买翡翠，别一上来就问最低价。")

    def test_image_prompt_without_persona_reference_rewrites_persona_visuals(self) -> None:
        create_response = self.client.post(
            "/api/projects",
            json={
                "project_name": "苹果姐翡翠",
                "industry": "珠宝",
                "sub_industry": "翡翠",
                "product": "老种阳绿圆条翡翠手镯",
                "personal_intro": "苹果姐，45岁直爽女性，卖翡翠多年",
                "target_audience": "喜欢高品质翡翠的人",
                "platforms": ["抖音"],
                "current_stage": "冷启动",
            },
        )
        project_id = create_response.json()["data"]["id"]
        bad_persona_prompt = (
            "一位45岁直爽女性（苹果姐）穿深色衬衫，右手持紫光手电从侧面照亮一只老种阳绿圆条翡翠手镯，"
            "左手托底，桌上有台湾老照片复印件、国检证书和卡尺。"
        )
        gateway_response = LLMGatewayResponse(
            success=True,
            provider="test",
            model="test-model",
            content="",
            data={
                "topics": [
                    {
                        "title": "紫光灯看老种阳绿手镯",
                        "content_type": "产品细节",
                        "platform": "抖音",
                        "goal": "获客",
                        "user_pain_point": "怕看不懂真假和种水",
                        "hook": "紫光灯一打，很多细节藏不住。",
                        "shooting_suggestion": "用紫光手电照手镯侧面。",
                        "conversion_method": "评论预算，私信发图咨询。",
                        "image_prompt": bad_persona_prompt,
                        "score": 90,
                    }
                ]
            },
            usage={},
            latency_ms=1,
        )

        with patch("app.services.topic_service.LLMGateway") as gateway_class:
            gateway_class.return_value.generate.return_value = gateway_response
            response = self.client.post(
                "/api/creation/topics/generate",
                json={
                    "project_id": project_id,
                    "platform": "抖音",
                    "goal": "获客",
                    "content_format": "image",
                    "count": 1,
                },
            )

        self.assertEqual(response.status_code, 200)
        image_prompt = response.json()["data"]["topics"][0]["topic_data"]["image_prompt"]
        self.assertNotIn("苹果姐", image_prompt)
        self.assertNotIn("45岁直爽女性", image_prompt)
        self.assertIn("货品主体", image_prompt)
        self.assertIn("非人设", image_prompt)

    def test_image_prompt_preserves_persona_visuals_when_reference_uploaded(self) -> None:
        create_response = self.client.post(
            "/api/projects",
            json={
                "project_name": "苹果姐翡翠",
                "industry": "珠宝",
                "sub_industry": "翡翠",
                "product": "老种阳绿圆条翡翠手镯",
                "personal_intro": "苹果姐，45岁直爽女性，卖翡翠多年",
                "target_audience": "喜欢高品质翡翠的人",
                "platforms": ["抖音"],
                "current_stage": "冷启动",
            },
        )
        project_id = create_response.json()["data"]["id"]
        persona_prompt = "一位45岁直爽女性（苹果姐）手持紫光手电检查阳绿翡翠手镯。"
        gateway_response = LLMGatewayResponse(
            success=True,
            provider="test",
            model="test-model",
            content="",
            data={
                "topics": [
                    {
                        "title": "紫光灯看老种阳绿手镯",
                        "content_type": "产品细节",
                        "platform": "抖音",
                        "goal": "获客",
                        "user_pain_point": "怕看不懂真假和种水",
                        "hook": "紫光灯一打，很多细节藏不住。",
                        "shooting_suggestion": "用紫光手电照手镯侧面。",
                        "conversion_method": "评论预算，私信发图咨询。",
                        "image_prompt": persona_prompt,
                        "score": 90,
                    }
                ]
            },
            usage={},
            latency_ms=1,
        )

        with patch("app.services.topic_service.LLMGateway") as gateway_class:
            gateway_class.return_value.generate.return_value = gateway_response
            response = self.client.post(
                "/api/creation/topics/generate",
                json={
                    "project_id": project_id,
                    "platform": "抖音",
                    "goal": "获客",
                    "content_format": "image",
                    "count": 1,
                    "persona_reference_image_uploaded": True,
                },
            )

        self.assertEqual(response.status_code, 200)
        image_prompt = response.json()["data"]["topics"][0]["topic_data"]["image_prompt"]
        self.assertIn("苹果姐", image_prompt)

    def test_generate_topics_accepts_markdown_json_from_text_output(self) -> None:
        create_response = self.client.post(
            "/api/projects",
            json={
                "project_name": "四会翡翠账号",
                "industry": "珠宝",
                "sub_industry": "翡翠",
                "product": "翡翠手镯",
                "personal_intro": "在四会卖翡翠多年",
                "target_audience": "想买翡翠但怕踩坑的人",
                "platforms": ["抖音"],
                "current_stage": "冷启动",
            },
        )
        project_id = create_response.json()["data"]["id"]

        gateway_response = LLMGatewayResponse(
            success=True,
            provider="test",
            model="test-model",
            content="",
            data={
                "text": """```json
{
  "topics": [
    {
      "title": "四会翡翠市场实拍：新手别只看颜色",
      "content_type": "源头展示",
      "platform": "抖音",
      "goal": "获客",
      "user_pain_point": "担心买贵或踩坑",
      "hook": "新手买翡翠，第一眼别只盯颜色。",
      "shooting_suggestion": "市场档口实拍，展示手镯颜色、种水和瑕疵细节。",
      "conversion_method": "评论预算和用途，私信发图帮忙判断。",
      "score": 91
    }
  ]
}
```"""
            },
            usage={},
            latency_ms=1,
        )

        with patch("app.services.topic_service.LLMGateway") as gateway_class:
            gateway_class.return_value.generate.return_value = gateway_response
            response = self.client.post(
                "/api/creation/topics/generate",
                json={"project_id": project_id, "platform": "抖音", "goal": "获客", "count": 10},
            )

        self.assertEqual(response.status_code, 200)
        topics = response.json()["data"]["topics"]
        self.assertEqual(len(topics), 1)
        self.assertEqual(topics[0]["title"], "四会翡翠市场实拍：新手别只看颜色")

    def test_generate_topics_accepts_jsonish_text_with_unquoted_field_value(self) -> None:
        create_response = self.client.post(
            "/api/projects",
            json={
                "project_name": "四会翡翠账号",
                "industry": "珠宝",
                "sub_industry": "翡翠",
                "product": "翡翠手镯",
                "personal_intro": "在四会卖翡翠多年",
                "target_audience": "想买翡翠但怕踩坑的人",
                "platforms": ["抖音"],
                "current_stage": "冷启动",
            },
        )
        project_id = create_response.json()["data"]["id"]

        gateway_response = LLMGatewayResponse(
            success=True,
            provider="test",
            model="test-model",
            content="",
            data={
                "text": """```json
{
  "topics": [
    {
      "title": "高端商务送礼首选：四会源头直供的帝王绿翡翠挂件",
      "content_type": "产品故事",
      "platform": "抖音",
      "goal": "获客",
      "user_pain_point": "寻找有品位、有价值的商务礼品",
      "hook": "这款帝王绿翡翠挂件，我找了整整3个月。",
      "shooting_suggestion":特写镜头展示翡翠挂件的细节，讲述来源故事，
      "conversion_method": "评论区留言送礼，私信获取专属商务礼盒服务",
      "score": 88
    }
  ]
}
```"""
            },
            usage={},
            latency_ms=1,
        )

        with patch("app.services.topic_service.LLMGateway") as gateway_class:
            gateway_class.return_value.generate.return_value = gateway_response
            response = self.client.post(
                "/api/creation/topics/generate",
                json={"project_id": project_id, "platform": "抖音", "goal": "获客", "count": 10},
            )

        self.assertEqual(response.status_code, 200)
        topics = response.json()["data"]["topics"]
        self.assertEqual(len(topics), 1)
        self.assertEqual(topics[0]["score"], 88)
        self.assertIn("特写镜头", topics[0]["topic_data"]["shooting_suggestion"])

    def test_generate_topics_rejects_successful_model_response_with_no_topics(self) -> None:
        create_response = self.client.post(
            "/api/projects",
            json={
                "project_name": "四会翡翠账号",
                "industry": "珠宝",
                "sub_industry": "翡翠",
                "product": "翡翠手镯",
                "personal_intro": "在四会卖翡翠多年",
                "target_audience": "想买翡翠但怕踩坑的人",
                "platforms": ["抖音"],
                "current_stage": "冷启动",
            },
        )
        project_id = create_response.json()["data"]["id"]

        gateway_response = LLMGatewayResponse(
            success=True,
            provider="test",
            model="test-model",
            content="no usable topics",
            data={"text": "no usable topics"},
            usage={},
            latency_ms=1,
        )

        with patch("app.services.topic_service.LLMGateway") as gateway_class:
            gateway_class.return_value.generate.return_value = gateway_response
            response = self.client.post(
                "/api/creation/topics/generate",
                json={"project_id": project_id, "platform": "抖音", "goal": "获客", "count": 10},
            )

        self.assertEqual(response.status_code, 502)


if __name__ == "__main__":
    unittest.main()
