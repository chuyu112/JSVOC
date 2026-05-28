import unittest
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.llm.llm_gateway import LLMGatewayResponse
from app.main import app
from app.models.credit import CreditTransaction
from app.models.hot_copy import HotCopyRewrite
from app.models import auth_account, credit, generation_record, hot_copy, llm_channel, project, user  # noqa: F401
from app.schemas.hot_copy import HotCopyMaterialManualCreate, HotCopyRewriteRequest
from app.services import hot_copy_service


class HotCopyApiTest(unittest.TestCase):
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
        self.user_id = self.register_user("owner", "owner@example.com")

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()
        from app.core.config import get_settings

        get_settings.cache_clear()
        self.env_patcher.stop()

    def register_user(self, username: str, email: str) -> int:
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
        return int(response.json()["data"]["user"]["id"])

    def create_project(self) -> int:
        response = self.client.post(
            "/api/projects",
            json={
                "project_name": "四会翡翠口播号",
                "industry": "珠宝",
                "sub_industry": "翡翠",
                "product": "翡翠手镯",
                "personal_intro": "在四会卖翡翠多年，擅长新手避坑。",
                "target_audience": "喜欢翡翠但怕踩坑的人",
                "platforms": ["抖音"],
                "current_stage": "冷启动",
            },
        )
        self.assertEqual(response.status_code, 201)
        return int(response.json()["data"]["id"])

    def create_material(self, **overrides) -> dict:
        payload = {
            "platform": "douyin",
            "title": "新手买翡翠别先问最低价",
            "original_script": "新手买翡翠，别一上来就问最低价。先看种水，再看纹裂，再看证书。",
            "source_url": "https://v.douyin.com/example/",
            "account_name": "四会源头老李",
            "metrics_json": {"likes": 12000, "comments": 600},
        }
        payload.update(overrides)
        response = self.client.post("/api/hot-copy/materials/manual", json=payload)
        self.assertEqual(response.status_code, 201)
        return response.json()["data"]

    def test_manual_material_requires_original_script(self) -> None:
        response = self.client.post(
            "/api/hot-copy/materials/manual",
            json={"platform": "douyin", "title": "爆款标题", "original_script": ""},
        )

        self.assertEqual(response.status_code, 422)

    def test_create_and_list_manual_materials(self) -> None:
        material = self.create_material()

        response = self.client.get("/api/hot-copy/materials")

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data[0]["id"], material["id"])
        self.assertEqual(data[0]["platform"], "douyin")
        self.assertEqual(data[0]["source_type"], "manual")

    def test_analyze_material_records_generation_history(self) -> None:
        material = self.create_material()

        response = self.client.post(f"/api/hot-copy/materials/{material['id']}/analyze")

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertIn("hook", data["analysis"])
        self.assertIsInstance(data["generation_record_id"], int)
        records = self.client.get("/api/generation-records?module_name=hot_copy_analysis").json()["data"]
        self.assertEqual(records[0]["id"], data["generation_record_id"])
        self.assertTrue(records[0]["output_data"]["success"])

    def test_rewrite_material_records_generation_history(self) -> None:
        project_id = self.create_project()
        material = self.create_material(project_id=project_id)
        analyze = self.client.post(f"/api/hot-copy/materials/{material['id']}/analyze")
        self.assertEqual(analyze.status_code, 200)

        response = self.client.post(
            f"/api/hot-copy/materials/{material['id']}/rewrite",
            json={
                "project_id": project_id,
                "rewrite_mode": "medium",
                "duration": "60s",
                "conversion_goal": "私信获客",
                "product": "翡翠手镯",
                "target_customer": "怕买贵的新手",
                "account_persona": "四会源头选品顾问",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertIn("script", data["output"])
        self.assertIsInstance(data["generation_record_id"], int)
        records = self.client.get("/api/generation-records?module_name=hot_copy_rewrite").json()["data"]
        self.assertEqual(records[0]["id"], data["generation_record_id"])
        self.assertTrue(records[0]["output_data"]["success"])

    def test_user_cannot_read_other_users_material(self) -> None:
        material = self.create_material()
        self.register_user("other", "other@example.com")

        detail = self.client.get(f"/api/hot-copy/materials/{material['id']}")
        analyze = self.client.post(f"/api/hot-copy/materials/{material['id']}/analyze")
        rewrite = self.client.post(
            f"/api/hot-copy/materials/{material['id']}/rewrite",
            json={
                "rewrite_mode": "medium",
                "duration": "60s",
                "conversion_goal": "私信获客",
            },
        )

        self.assertEqual(detail.status_code, 404)
        self.assertEqual(analyze.status_code, 404)
        self.assertEqual(rewrite.status_code, 404)

    def test_redianbao_search_returns_reserved_message(self) -> None:
        response = self.client.post(
            "/api/hot-copy/redianbao/search",
            json={"keyword": "翡翠口播", "platform": "douyin", "count": 30},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["success"])
        self.assertEqual(payload["data"]["items"], [])
        self.assertIn("热点宝", payload["message"])

    def test_auto_material_parser_runtime_error_returns_502(self) -> None:
        with patch("app.services.hot_copy_service.parse_video_link", side_effect=RuntimeError("暂不支持该平台自动解析")):
            response = self.client.post(
                "/api/hot-copy/materials/auto",
                json={"source_url": "https://channels.weixin.qq.com/web/pages/feed?exportkey=test"},
            )

        self.assertEqual(response.status_code, 502)
        self.assertIn("暂不支持", response.json()["detail"])

    def test_import_douyin_profile_returns_recent_videos_and_desc_quality(self) -> None:
        import_result = {
            "profile": {"sec_user_id": "sec-user-1", "nickname": "Account Name"},
            "videos": [
                {"aweme_id": "aweme-1", "desc": "够长的文案。第二句也有结构。第三句继续展开重点。", "desc_qualified": True}
            ],
            "desc_quality": {"total": 1, "qualified": 1, "qualified_percent": 100.0},
        }
        with patch("app.api.hot_copy.video_parsing_service.import_douyin_profile_videos", return_value=import_result) as mocked:
            response = self.client.post(
                "/api/hot-copy/douyin-profile/import",
                json={"source_url": "https://www.douyin.com/user/sec-user-1", "count": 30},
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["profile"]["nickname"], "Account Name")
        self.assertEqual(data["desc_quality"]["qualified_percent"], 100.0)
        mocked.assert_called_once_with("https://www.douyin.com/user/sec-user-1", count=30)

    def test_transcribe_douyin_profile_video_returns_asr_text(self) -> None:
        transcribe_result = {
            "aweme_id": "aweme-1",
            "title": "short title",
            "text": "full spoken script",
            "segments": [],
            "duration": 12.3,
            "source_video_oss_key": "users/1/account/references/videos/test.mp4",
            "source_video_url": "https://oss.example.test/signed.mp4",
            "source_video_url_expires_at": 1710000100,
        }
        with patch(
            "app.api.hot_copy.video_parsing_service.transcribe_douyin_profile_video",
            return_value=transcribe_result,
        ) as mocked:
            response = self.client.post(
                "/api/hot-copy/douyin-profile/transcribe",
                json={
                    "aweme_id": "aweme-1",
                    "title": "short title",
                    "media_url": "https://v26-web.douyinvod.com/video.mp4",
                },
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["text"], "full spoken script")
        mocked.assert_called_once_with(
            media_url="https://v26-web.douyinvod.com/video.mp4",
            aweme_id="aweme-1",
            title="short title",
            user_id=self.user_id,
            project_id=None,
        )

    def test_analyze_rejects_malformed_gateway_output_without_persist_or_charge(self) -> None:
        db = self.SessionLocal()
        try:
            material = hot_copy_service.create_manual_material(
                db,
                HotCopyMaterialManualCreate(
                    platform="douyin",
                    title="爆款标题",
                    original_script="爆款口播内容",
                ),
                self.user_id,
            )
            malformed_result = LLMGatewayResponse(
                success=True,
                provider="mock",
                model="mock-model",
                content="{}",
                data={"hook": "only hook"},
                usage={},
                latency_ms=1,
                generation_record_id=123,
            )

            with patch("app.services.hot_copy_service.LLMGateway.generate", return_value=malformed_result):
                with self.assertRaises(HTTPException) as raised:
                    hot_copy_service.analyze_material(db, material.id, self.user_id)

            self.assertEqual(raised.exception.status_code, 502)
            db.refresh(material)
            self.assertIsNone(material.analysis_json)
            charges = db.scalars(
                select(CreditTransaction).where(CreditTransaction.reason == "hot_copy_analysis")
            ).all()
            self.assertEqual(len(charges), 0)
        finally:
            db.close()

    def test_rewrite_rejects_missing_generation_record_id_without_persist_or_charge(self) -> None:
        db = self.SessionLocal()
        try:
            material = hot_copy_service.create_manual_material(
                db,
                HotCopyMaterialManualCreate(
                    platform="douyin",
                    title="爆款标题",
                    original_script="爆款口播内容",
                ),
                self.user_id,
            )
            material.analysis_json = {
                "hook": "反常识开头",
                "structure": ["开头", "转化"],
                "emotion_triggers": ["怕买贵"],
                "trust_builders": ["源头经验"],
                "conversion_points": ["私信"],
                "risk_notes": ["不要照搬"],
            }
            db.add(material)
            db.commit()
            valid_result_without_record = LLMGatewayResponse(
                success=True,
                provider="mock",
                model="mock-model",
                content="{}",
                data={
                    "title": "新标题",
                    "hook": "新钩子",
                    "script": "原创口播文案",
                    "shot_suggestions": ["真人出镜"],
                    "conversion_script": "私信发图",
                    "risk_notes": ["不要承诺绝对效果"],
                },
                usage={},
                latency_ms=1,
                generation_record_id=None,
            )

            with patch("app.services.hot_copy_service.LLMGateway.generate", return_value=valid_result_without_record):
                with self.assertRaises(HTTPException) as raised:
                    hot_copy_service.rewrite_material(
                        db,
                        material.id,
                        HotCopyRewriteRequest(
                            rewrite_mode="medium",
                            duration="60s",
                            conversion_goal="私信获客",
                        ),
                        self.user_id,
                    )

            self.assertEqual(raised.exception.status_code, 502)
            rewrites = db.scalars(select(HotCopyRewrite)).all()
            self.assertEqual(len(rewrites), 0)
            charges = db.scalars(
                select(CreditTransaction).where(CreditTransaction.reason == "hot_copy_rewrite")
            ).all()
            self.assertEqual(len(charges), 0)
        finally:
            db.close()
