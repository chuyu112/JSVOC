import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


class ImageGenerationApiTest(unittest.TestCase):
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

        register_response = self.client.post(
            "/api/auth/register",
            json={
                "display_name": "Owner",
                "username": "owner",
                "email": "owner@example.com",
                "password": "StrongPass123",
            },
        )
        self.assertEqual(register_response.status_code, 201)

        project_response = self.client.post(
            "/api/projects",
            json={
                "project_name": "翡翠测试",
                "industry": "珠宝",
                "sub_industry": "翡翠",
                "product": "翡翠",
                "personal_intro": "在四会卖翡翠",
                "target_audience": "想买翡翠的人",
                "platforms": ["抖音"],
                "current_stage": "冷启动",
            },
        )
        self.assertEqual(project_response.status_code, 201)
        self.project_id = project_response.json()["data"]["id"]

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_generate_image_routes_moyu_chat_base_to_images_endpoint(self) -> None:
        calls = []

        def fake_post(url, headers, json, timeout):
            calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
            return httpx.Response(
                200,
                json={
                    "created": 1760000000,
                    "data": [{"b64_json": "ZmFrZS1wbmc="}],
                    "usage": {"total_tokens": 12},
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

        with (
            patch("app.services.image_generation_service.get_settings", return_value=settings),
            patch("app.services.image_generation_service.httpx.post", side_effect=fake_post),
        ):
            response = self.client.post(
                "/api/creation/images/generate",
                json={
                    "project_id": 1,
                    "prompt": "A clean product photo of a jade bracelet",
                    "size": "1536x1024",
                    "quality": "medium",
                },
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["provider"], "moyu")
        self.assertEqual(body["data"]["model"], "gpt-image-2")
        self.assertEqual(body["data"]["images"][0]["b64_json"], "ZmFrZS1wbmc=")
        self.assertEqual(body["data"]["images"][0]["data_url"], "data:image/png;base64,ZmFrZS1wbmc=")
        self.assertEqual(body["data"]["usage"]["total_tokens"], 12)
        self.assertIsInstance(body["data"]["latency_ms"], int)

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["url"], "https://www.moyu.info/v1/images/generations")
        self.assertEqual(calls[0]["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(
            calls[0]["json"],
            {
                "model": "gpt-image-2",
                "prompt": "A clean product photo of a jade bracelet",
                "n": 1,
                "size": "1536x1024",
                "quality": "medium",
            },
        )
        self.assertEqual(calls[0]["timeout"], 180.0)

    def test_generate_image_rejects_unsupported_size(self) -> None:
        response = self.client.post(
            "/api/creation/images/generate",
            json={"prompt": "jade bracelet", "size": "512x512", "quality": "medium"},
        )

        self.assertEqual(response.status_code, 422)

    def test_generate_image_accepts_2k_experimental_size(self) -> None:
        calls = []

        def fake_post(url, headers, json, timeout):
            calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
            return httpx.Response(
                200,
                json={
                    "model": "gpt-image-2",
                    "data": [{"b64_json": "ZmFrZS0yay1wbmc="}],
                },
                request=httpx.Request("POST", url),
            )

        settings = Settings(
            LLM_PROVIDER="moyu",
            LLM_BASE_URL="https://www.moyu.info/v1",
            LLM_API_KEY="test-key",
            LLM_MODEL="deepseek-v4-flash",
            LLM_TIMEOUT_SECONDS=180,
        )

        with (
            patch("app.services.image_generation_service.get_settings", return_value=settings),
            patch("app.services.image_generation_service.httpx.post", side_effect=fake_post),
        ):
            response = self.client.post(
                "/api/creation/images/generate",
                json={"prompt": "jade bracelet", "size": "2048x1152", "quality": "low"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(calls[0]["json"]["size"], "2048x1152")

    def test_generate_image_retries_transient_gateway_timeout(self) -> None:
        calls = []

        def fake_post(url, headers, json, timeout):
            calls.append({"url": url, "json": json})
            if len(calls) == 1:
                return httpx.Response(
                    504,
                    text="<html><h1>504 Gateway Time-out</h1></html>",
                    request=httpx.Request("POST", url),
                )
            return httpx.Response(
                200,
                json={"data": [{"b64_json": "cmV0cmllZC1pbWFnZQ=="}]},
                request=httpx.Request("POST", url),
            )

        settings = Settings(
            LLM_PROVIDER="openai_compatible",
            LLM_BASE_URL="http://api.kakayiduo.cloud/v1",
            LLM_API_KEY="test-key",
            LLM_MODEL="gpt-5.5",
        )

        with (
            patch("app.services.image_generation_service.get_settings", return_value=settings),
            patch("app.services.image_generation_service.httpx.post", side_effect=fake_post),
        ):
            response = self.client.post(
                "/api/creation/images/generate",
                json={"prompt": "A clean product photo of a jade bracelet"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(calls), 2)
        self.assertEqual(response.json()["data"]["images"][0]["b64_json"], "cmV0cmllZC1pbWFnZQ==")

    def test_edit_image_routes_uploaded_base64_to_moyu_edits_endpoint(self) -> None:
        calls = []

        def fake_post(url, headers, data, files, timeout):
            calls.append(
                {
                    "url": url,
                    "headers": headers,
                    "data": data,
                    "files": files,
                    "timeout": timeout,
                }
            )
            return httpx.Response(
                200,
                json={
                    "created": 1760000000,
                    "data": [{"b64_json": "ZWRpdGVkLXBuZw=="}],
                    "usage": {"total_tokens": 18},
                },
                request=httpx.Request("POST", url),
            )

        settings = Settings(
            LLM_PROVIDER="moyu",
            LLM_BASE_URL="https://www.moyu.info/v1/chat/completions",
            LLM_API_KEY="test-key",
            LLM_MODEL="deepseek-v4-flash",
            LLM_TIMEOUT_SECONDS=6,
        )

        with (
            patch("app.services.image_generation_service.get_settings", return_value=settings),
            patch("app.services.image_generation_service.httpx.post", side_effect=fake_post),
        ):
            response = self.client.post(
                "/api/creation/images/edit",
                json={
                    "project_id": 1,
                    "prompt": "Keep the jade bracelet, make the light softer",
                    "source_image_base64": "ZmFrZS1pbWFnZQ==",
                    "source_image_mime": "image/png",
                    "source_image_filename": "source.png",
                    "size": "1024x1024",
                    "quality": "medium",
                },
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["provider"], "moyu")
        self.assertEqual(body["data"]["model"], "gpt-image-2")
        self.assertEqual(body["data"]["images"][0]["data_url"], "data:image/png;base64,ZWRpdGVkLXBuZw==")

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["url"], "https://www.moyu.info/v1/images/edits")
        self.assertEqual(calls[0]["headers"]["Authorization"], "Bearer test-key")
        self.assertNotIn("Content-Type", calls[0]["headers"])
        self.assertEqual(calls[0]["data"]["model"], "gpt-image-2")
        self.assertIn("Keep the jade bracelet, make the light softer", calls[0]["data"]["prompt"])
        self.assertIn("参考图类型：货品参考图", calls[0]["data"]["prompt"])
        self.assertEqual(calls[0]["data"]["n"], "1")
        self.assertEqual(calls[0]["data"]["size"], "1024x1024")
        self.assertEqual(calls[0]["data"]["quality"], "medium")
        self.assertEqual(calls[0]["files"][0], ("image", ("source.png", b"fake-image", "image/png")))
        self.assertEqual(calls[0]["timeout"], 180.0)

    def test_edit_image_accepts_up_to_three_references_per_type(self) -> None:
        calls = []

        def fake_post(url, headers, data, files, timeout):
            calls.append({"data": data, "files": files})
            return httpx.Response(
                200,
                json={"data": [{"b64_json": "ZWRpdGVkLXBuZw=="}]},
                request=httpx.Request("POST", url),
            )

        settings = Settings(
            LLM_PROVIDER="openai_compatible",
            LLM_BASE_URL="http://api.kakayiduo.cloud/v1",
            LLM_API_KEY="test-key",
            LLM_MODEL="gpt-5.5",
        )
        reference_images = []
        for reference_type in ("persona", "product", "location"):
            for index in range(3):
                reference_images.append(
                    {
                        "reference_image_type": reference_type,
                        "source_image_base64": "ZmFrZS1pbWFnZQ==",
                        "source_image_mime": "image/png",
                        "source_image_filename": f"{reference_type}-{index}.png",
                    }
                )

        with (
            patch("app.services.image_generation_service.get_settings", return_value=settings),
            patch("app.services.image_generation_service.httpx.post", side_effect=fake_post),
        ):
            response = self.client.post(
                "/api/creation/images/edit",
                json={
                    "project_id": 1,
                    "prompt": "生成苹果姐在公司档口展示阳绿翡翠手镯",
                    "reference_images": reference_images,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(calls[0]["files"]), 9)
        self.assertIn("参考图类型：人设参考图、货品参考图、场景参考图", calls[0]["data"]["prompt"])
        self.assertIn("人设图1：人设参考图，文件名 persona-0.png。", calls[0]["data"]["prompt"])
        self.assertIn("货品图1：货品参考图，文件名 product-0.png。", calls[0]["data"]["prompt"])
        self.assertIn("场景图1：场景参考图，文件名 location-0.png。", calls[0]["data"]["prompt"])

    def test_edit_image_rejects_more_than_three_references_per_type(self) -> None:
        reference_images = [
            {
                "reference_image_type": "product",
                "source_image_base64": "ZmFrZS1pbWFnZQ==",
                "source_image_mime": "image/png",
                "source_image_filename": f"product-{index}.png",
            }
            for index in range(4)
        ]

        response = self.client.post(
            "/api/creation/images/edit",
            json={"prompt": "jade bracelet", "reference_images": reference_images},
        )

        self.assertEqual(response.status_code, 422)

    def test_edit_image_requires_at_least_one_reference_image(self) -> None:
        response = self.client.post(
            "/api/creation/images/edit",
            json={"prompt": "jade bracelet", "reference_images": []},
        )

        self.assertEqual(response.status_code, 422)

    def test_edit_image_rejects_unsupported_reference_image_mime(self) -> None:
        response = self.client.post(
            "/api/creation/images/edit",
            json={
                "prompt": "jade bracelet",
                "reference_images": [
                    {
                        "reference_image_type": "product",
                        "source_image_base64": "ZmFrZS1pbWFnZQ==",
                        "source_image_mime": "image/heic",
                        "source_image_filename": "product.heic",
                    }
                ],
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("仅支持 PNG、JPEG、WebP", response.json()["detail"])

    def test_edit_image_product_reference_focuses_goods_and_scene_not_persona(self) -> None:
        calls = []

        def fake_post(url, headers, data, files, timeout):
            calls.append(data)
            return httpx.Response(
                200,
                json={"data": [{"b64_json": "ZWRpdGVkLXBuZw=="}]},
                request=httpx.Request("POST", url),
            )

        settings = Settings(
            LLM_PROVIDER="openai_compatible",
            LLM_BASE_URL="http://api.kakayiduo.cloud/v1",
            LLM_API_KEY="test-key",
            LLM_MODEL="gpt-5.5",
        )

        with (
            patch("app.services.image_generation_service.get_settings", return_value=settings),
            patch("app.services.image_generation_service.httpx.post", side_effect=fake_post),
        ):
            response = self.client.post(
                "/api/creation/images/edit",
                json={
                    "project_id": 1,
                    "prompt": "生成苹果姐在档口拿着阳绿翡翠手镯的画面",
                    "source_image_base64": "ZmFrZS1pbWFnZQ==",
                    "source_image_mime": "image/png",
                    "source_image_filename": "bracelet.png",
                    "reference_image_types": ["product"],
                },
            )

        self.assertEqual(response.status_code, 200)
        prompt = calls[0]["prompt"]
        self.assertIn("参考图类型：货品参考图", prompt)
        self.assertIn("重点生成货品主体和场景", prompt)
        self.assertIn("不要生成可识别的人设本人", prompt)

    def test_edit_image_persona_reference_allows_new_person_goods_scene(self) -> None:
        calls = []

        def fake_post(url, headers, data, files, timeout):
            calls.append(data)
            return httpx.Response(
                200,
                json={"data": [{"b64_json": "ZWRpdGVkLXBuZw=="}]},
                request=httpx.Request("POST", url),
            )

        settings = Settings(
            LLM_PROVIDER="openai_compatible",
            LLM_BASE_URL="http://api.kakayiduo.cloud/v1",
            LLM_API_KEY="test-key",
            LLM_MODEL="gpt-5.5",
        )

        with (
            patch("app.services.image_generation_service.get_settings", return_value=settings),
            patch("app.services.image_generation_service.httpx.post", side_effect=fake_post),
        ):
            response = self.client.post(
                "/api/creation/images/edit",
                json={
                    "project_id": 1,
                    "prompt": "生成苹果姐在档口拿着阳绿翡翠手镯的画面",
                    "source_image_base64": "ZmFrZS1pbWFnZQ==",
                    "source_image_mime": "image/png",
                    "source_image_filename": "apple-sister.png",
                    "reference_image_types": ["persona"],
                },
            )

        self.assertEqual(response.status_code, 200)
        prompt = calls[0]["prompt"]
        self.assertIn("参考图类型：人设参考图", prompt)
        self.assertIn("可以生成新的人、货、场组合", prompt)
        self.assertIn("以参考图人物为唯一人设依据", prompt)

    def test_edit_image_location_reference_focuses_location_and_goods_not_persona(self) -> None:
        calls = []

        def fake_post(url, headers, data, files, timeout):
            calls.append(data)
            return httpx.Response(
                200,
                json={"data": [{"b64_json": "ZWRpdGVkLXBuZw=="}]},
                request=httpx.Request("POST", url),
            )

        settings = Settings(
            LLM_PROVIDER="openai_compatible",
            LLM_BASE_URL="http://api.kakayiduo.cloud/v1",
            LLM_API_KEY="test-key",
            LLM_MODEL="gpt-5.5",
        )

        with (
            patch("app.services.image_generation_service.get_settings", return_value=settings),
            patch("app.services.image_generation_service.httpx.post", side_effect=fake_post),
        ):
            response = self.client.post(
                "/api/creation/images/edit",
                json={
                    "project_id": 1,
                    "prompt": "生成公司档口里的阳绿翡翠手镯陈列图",
                    "source_image_base64": "ZmFrZS1pbWFnZQ==",
                    "source_image_mime": "image/png",
                    "source_image_filename": "booth.png",
                    "reference_image_types": ["location"],
                },
            )

        self.assertEqual(response.status_code, 200)
        prompt = calls[0]["prompt"]
        self.assertIn("参考图类型：场景参考图", prompt)
        self.assertIn("参考场景空间", prompt)
        self.assertIn("重点生成货品主体和场景", prompt)

    def test_edit_image_product_and_location_references_focus_goods_scene_without_persona(self) -> None:
        calls = []

        def fake_post(url, headers, data, files, timeout):
            calls.append(data)
            return httpx.Response(
                200,
                json={"data": [{"b64_json": "ZWRpdGVkLXBuZw=="}]},
                request=httpx.Request("POST", url),
            )

        settings = Settings(
            LLM_PROVIDER="openai_compatible",
            LLM_BASE_URL="http://api.kakayiduo.cloud/v1",
            LLM_API_KEY="test-key",
            LLM_MODEL="gpt-5.5",
        )

        with (
            patch("app.services.image_generation_service.get_settings", return_value=settings),
            patch("app.services.image_generation_service.httpx.post", side_effect=fake_post),
        ):
            response = self.client.post(
                "/api/creation/images/edit",
                json={
                    "project_id": 1,
                    "prompt": "生成苹果姐在公司档口展示阳绿翡翠手镯",
                    "source_image_base64": "ZmFrZS1pbWFnZQ==",
                    "source_image_mime": "image/png",
                    "source_image_filename": "booth-bracelet.png",
                    "reference_image_types": ["product", "location"],
                },
            )

        self.assertEqual(response.status_code, 200)
        prompt = calls[0]["prompt"]
        self.assertIn("参考图类型：货品参考图、场景参考图", prompt)
        self.assertIn("重点生成货品主体和场景", prompt)
        self.assertIn("不要生成可识别的人设本人", prompt)

    def test_edit_image_all_reference_types_allow_person_goods_scene(self) -> None:
        calls = []

        def fake_post(url, headers, data, files, timeout):
            calls.append(data)
            return httpx.Response(
                200,
                json={"data": [{"b64_json": "ZWRpdGVkLXBuZw=="}]},
                request=httpx.Request("POST", url),
            )

        settings = Settings(
            LLM_PROVIDER="openai_compatible",
            LLM_BASE_URL="http://api.kakayiduo.cloud/v1",
            LLM_API_KEY="test-key",
            LLM_MODEL="gpt-5.5",
        )

        with (
            patch("app.services.image_generation_service.get_settings", return_value=settings),
            patch("app.services.image_generation_service.httpx.post", side_effect=fake_post),
        ):
            response = self.client.post(
                "/api/creation/images/edit",
                json={
                    "project_id": 1,
                    "prompt": "生成苹果姐在公司档口展示阳绿翡翠手镯",
                    "source_image_base64": "ZmFrZS1pbWFnZQ==",
                    "source_image_mime": "image/png",
                    "source_image_filename": "person-product-location.png",
                    "reference_image_types": ["persona", "product", "location"],
                },
            )

        self.assertEqual(response.status_code, 200)
        prompt = calls[0]["prompt"]
        self.assertIn("参考图类型：人设参考图、货品参考图、场景参考图", prompt)
        self.assertIn("可以生成新的人、货、场组合", prompt)


if __name__ == "__main__":
    unittest.main()


class ImageGenerationOssApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        from app.models import auth_account  # noqa: F401
        from app.models import digital_asset  # noqa: F401
        from app.models import generation_record  # noqa: F401
        from app.models import project  # noqa: F401
        from app.models import user  # noqa: F401

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
        self.project_id = self.create_project()

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def register_user(self) -> None:
        response = self.client.post(
            "/api/auth/register",
            json={
                "display_name": "Owner",
                "username": "owner",
                "email": "owner@example.com",
                "password": "StrongPass123",
            },
        )
        self.assertEqual(response.status_code, 201)

    def create_project(self) -> int:
        response = self.client.post(
            "/api/projects",
            json={
                "project_name": "jade image project",
                "industry": "jewelry",
                "sub_industry": "jade",
                "product": "jade bracelet",
                "personal_intro": "seller",
                "target_audience": "buyers",
                "platforms": ["douyin"],
                "current_stage": "stable",
            },
        )
        self.assertEqual(response.status_code, 201)
        return response.json()["data"]["id"]

    def test_generate_image_uploads_to_oss_and_creates_image_asset(self) -> None:
        calls = []

        def fake_post(url, headers, json, timeout):
            calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
            return httpx.Response(
                200,
                json={"data": [{"b64_json": "ZmFrZS1wbmc="}]},
                request=httpx.Request("POST", url),
            )

        settings = Settings(
            LLM_PROVIDER="openai_compatible",
            LLM_BASE_URL="http://api.kakayiduo.cloud/v1",
            LLM_API_KEY="test-key",
            LLM_MODEL="gpt-5.5",
            OSS_ACCESS_KEY_ID="test-oss-key",
            OSS_ACCESS_KEY_SECRET="test-oss-secret",
            OSS_ENDPOINT="https://oss-cn-beijing.aliyuncs.com",
            OSS_BUCKET_NAME="jsvoc-assets",
            OSS_URL_EXPIRE_SECONDS=600,
        )

        with (
            patch("app.services.image_generation_service.get_settings", return_value=settings),
            patch("app.services.image_generation_service.httpx.post", side_effect=fake_post),
            patch("app.services.storage_service.get_settings", return_value=settings),
            patch("app.services.storage_service.upload_bytes", return_value="users/1/images/test.png"),
            patch(
                "app.services.storage_service.sign_get_url",
                return_value=("https://signed.example.com/users/1/images/test.png", 1760000600),
            ),
        ):
            response = self.client.post(
                "/api/creation/images/generate",
                json={
                    "project_id": self.project_id,
                    "prompt": "A clean product photo of a jade bracelet",
                    "size": "1536x1024",
                    "quality": "medium",
                },
            )
            assets_response = self.client.get("/api/digital-assets")

        self.assertEqual(response.status_code, 200)
        image = response.json()["data"]["images"][0]
        self.assertEqual(image["url"], "https://signed.example.com/users/1/images/test.png")
        self.assertEqual(image["oss_object_key"], "users/1/images/test.png")
        self.assertEqual(image["asset_id"], 1)
        self.assertIsNone(image["b64_json"])
        self.assertIsNone(image["data_url"])

        self.assertEqual(assets_response.status_code, 200)
        assets = assets_response.json()["data"]
        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0]["asset_type"], "image")
        self.assertIsNone(assets[0]["source_project_id"])
        self.assertEqual(assets[0]["project_snapshot"]["scope"], "account")
        self.assertEqual(assets[0]["asset_metadata"]["source_project"]["project_id"], self.project_id)
        self.assertEqual(assets[0]["oss_object_key"], "users/1/images/test.png")
        self.assertEqual(assets[0]["access_url"], "https://signed.example.com/users/1/images/test.png")
