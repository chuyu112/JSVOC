import base64
from datetime import timedelta
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import auth_account  # noqa: F401
from app.models import digital_asset  # noqa: F401
from app.models import generation_record  # noqa: F401
from app.models import generation_task  # noqa: F401
from app.models import project  # noqa: F401
from app.models import user  # noqa: F401
from app.models.digital_asset import DigitalAsset
from app.models.generation_record import GenerationRecord
from app.models.generation_task import GenerationTask
from app.core.datetime_utils import utcnow_naive
from app.services.generation_task_service import fail_stale_generation_tasks


class GenerationTasksApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
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
        self.register_user(self.client, "owner", "owner@example.com")

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def register_user(self, client: TestClient, username: str, email: str) -> int:
        response = client.post(
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

    def create_project(self, client: TestClient) -> int:
        response = client.post(
            "/api/projects",
            json={
                "project_name": "jade project",
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
        return int(response.json()["data"]["id"])

    def test_get_generation_task_returns_current_status(self) -> None:
        owner_user_id = 1
        with self.SessionLocal() as db:
            task = GenerationTask(
                task_type="image_generate",
                status="succeeded",
                user_id=owner_user_id,
                project_id=7,
                input_data={"prompt": "jade bracelet"},
                result_data={"images": [{"url": "https://example.test/image.png"}]},
            )
            db.add(task)
            db.commit()
            task_id = task.id

        response = self.client.get(f"/api/generation-tasks/{task_id}")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["id"], task_id)
        self.assertEqual(body["data"]["task_type"], "image_generate")
        self.assertEqual(body["data"]["status"], "succeeded")
        self.assertEqual(body["data"]["project_id"], 7)
        self.assertEqual(body["data"]["result_data"]["images"][0]["url"], "https://example.test/image.png")

    def test_get_generation_task_is_scoped_to_current_user(self) -> None:
        with self.SessionLocal() as db:
            task = GenerationTask(
                task_type="image_generate",
                status="queued",
                user_id=1,
                project_id=7,
                input_data={"prompt": "jade bracelet"},
            )
            db.add(task)
            db.commit()
            task_id = task.id

        other_client = TestClient(app)
        self.register_user(other_client, "other", "other@example.com")
        response = other_client.get(f"/api/generation-tasks/{task_id}")

        self.assertEqual(response.status_code, 404)

    def test_list_generation_tasks_returns_recent_tasks_for_current_user_with_errors(self) -> None:
        with self.SessionLocal() as db:
            own_failed = GenerationTask(
                task_type="image_edit",
                status="failed",
                user_id=1,
                project_id=None,
                input_data={"prompt": "jade pendant"},
                error_message="image generation provider failed 400: moderation_blocked",
                created_at=utcnow_naive() - timedelta(minutes=1),
                updated_at=utcnow_naive() - timedelta(minutes=1),
            )
            own_success = GenerationTask(
                task_type="video_generate",
                status="succeeded",
                user_id=1,
                project_id=7,
                input_data={"prompt": "jade video"},
                result_data={"video_url": "https://example.test/video.mp4"},
                created_at=utcnow_naive() - timedelta(minutes=2),
                updated_at=utcnow_naive() - timedelta(minutes=2),
            )
            other_user_task = GenerationTask(
                task_type="image_generate",
                status="failed",
                user_id=999,
                project_id=None,
                input_data={"prompt": "private"},
                error_message="should not leak",
                created_at=utcnow_naive(),
                updated_at=utcnow_naive(),
            )
            db.add_all([own_failed, own_success, other_user_task])
            db.commit()

        response = self.client.get("/api/generation-tasks?limit=5")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        tasks = body["data"]
        self.assertEqual([item["task_type"] for item in tasks], ["image_edit", "video_generate"])
        self.assertEqual(tasks[0]["status"], "failed")
        self.assertIn("moderation_blocked", tasks[0]["error_message"])
        self.assertEqual(tasks[1]["status"], "succeeded")
        self.assertEqual(tasks[1]["result_data"]["video_url"], "https://example.test/video.mp4")

    def test_list_generation_tasks_summary_omits_large_payload_fields(self) -> None:
        with self.SessionLocal() as db:
            task = GenerationTask(
                task_type="video_generate",
                status="failed",
                user_id=1,
                project_id=7,
                input_data={"inline_reference_media": "x" * 1_000_000},
                result_data={"raw_provider_response": "y" * 1_000_000},
                error_message="provider failed",
            )
            db.add(task)
            db.commit()

        response = self.client.get("/api/generation-tasks?limit=5&summary=true")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(len(body["data"]), 1)
        item = body["data"][0]
        self.assertEqual(item["task_type"], "video_generate")
        self.assertEqual(item["status"], "failed")
        self.assertEqual(item["error_message"], "provider failed")
        self.assertNotIn("input_data", item)
        self.assertNotIn("result_data", item)

    def test_completed_image_task_creates_success_generation_record(self) -> None:
        from app.services.generation_record_service import create_generation_record_from_task

        with self.SessionLocal() as db:
            task = GenerationTask(
                task_type="image_generate",
                status="succeeded",
                user_id=1,
                project_id=7,
                input_data={"prompt": "jade bracelet", "size": "1024x1024"},
                result_data={
                    "provider": "openai_compatible",
                    "model": "gpt-image-2",
                    "images": [{"url": "https://example.test/image.png"}],
                    "usage": {"total_tokens": 12},
                    "latency_ms": 456,
                },
                started_at=utcnow_naive() - timedelta(seconds=1),
                completed_at=utcnow_naive(),
            )
            db.add(task)
            db.commit()
            db.refresh(task)

            record = create_generation_record_from_task(db, task)
            duplicate = create_generation_record_from_task(db, task)

            self.assertEqual(record.id, duplicate.id)
            self.assertEqual(record.module_name, "image_generate")
            self.assertEqual(record.user_id, 1)
            self.assertEqual(record.project_id, 7)
            self.assertEqual(record.model_provider, "openai_compatible")
            self.assertEqual(record.model_name, "gpt-image-2")
            self.assertEqual(record.token_usage["total_tokens"], 12)
            self.assertEqual(record.latency_ms, 456)
            self.assertTrue(record.output_data["success"])
            self.assertEqual(record.output_data["status"], "succeeded")
            self.assertEqual(record.output_data["data"]["images"][0]["url"], "https://example.test/image.png")
            self.assertEqual(record.input_data["metadata"]["generation_task_id"], task.id)

            records = list(db.scalars(select(GenerationRecord)).all())
            self.assertEqual(len(records), 1)

    def test_failed_video_task_creates_generation_record_with_reason(self) -> None:
        from app.services.generation_record_service import create_generation_record_from_task

        with self.SessionLocal() as db:
            task = GenerationTask(
                task_type="video_generate",
                status="failed",
                user_id=1,
                project_id=7,
                input_data={
                    "prompt": "jade bracelet video",
                    "options": {"model": "seedance-test", "ratio": "9:16"},
                },
                result_data={"provider": "seedance", "model": "seedance-test", "task_id": "cgt-test-1"},
                error_message="provider moderation blocked",
                started_at=utcnow_naive() - timedelta(seconds=2),
                completed_at=utcnow_naive(),
            )
            db.add(task)
            db.commit()
            db.refresh(task)

            record = create_generation_record_from_task(db, task)

            self.assertEqual(record.module_name, "video_generate")
            self.assertEqual(record.model_provider, "seedance")
            self.assertEqual(record.model_name, "seedance-test")
            self.assertFalse(record.output_data["success"])
            self.assertEqual(record.output_data["status"], "failed")
            self.assertEqual(record.output_data["failure_reason"], "provider moderation blocked")
            self.assertEqual(record.output_data["error"], "provider moderation blocked")
            self.assertEqual(record.output_data["data"]["task_id"], "cgt-test-1")

    def test_generate_image_async_creates_task_and_schedules_background_work(self) -> None:
        scheduled = []
        project_id = self.create_project(self.client)

        def fake_add_task(func, *args, **kwargs):
            scheduled.append({"func": func, "args": args, "kwargs": kwargs})

        with patch("fastapi.BackgroundTasks.add_task", side_effect=fake_add_task):
            response = self.client.post(
                "/api/creation/images/generate/async",
                json={"project_id": project_id, "prompt": "jade bracelet"},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["status"], "queued")
        self.assertIsInstance(body["data"]["task_id"], int)
        self.assertEqual(len(scheduled), 1)

        with self.SessionLocal() as db:
            task = db.scalar(select(GenerationTask).where(GenerationTask.id == body["data"]["task_id"]))
            self.assertIsNotNone(task)
            self.assertEqual(task.task_type, "image_generate")
            self.assertEqual(task.status, "queued")
            self.assertEqual(task.project_id, project_id)
            self.assertEqual(task.user_id, 1)
            self.assertEqual(task.input_data["prompt"], "jade bracelet")

    def test_generate_video_async_creates_task_and_schedules_background_work(self) -> None:
        scheduled = []
        project_id = self.create_project(self.client)

        def fake_add_task(func, *args, **kwargs):
            scheduled.append({"func": func, "args": args, "kwargs": kwargs})

        with patch("fastapi.BackgroundTasks.add_task", side_effect=fake_add_task):
            response = self.client.post(
                "/api/creation/videos/generate/async",
                json={
                    "project_id": project_id,
                    "prompt": "jade bracelet video",
                    "options": {"ratio": "9:16", "resolution": "1080p"},
                    "reference_images": ["https://assets.example.test/storyboard.png"],
                    "reference_videos": ["https://assets.example.test/reference.mp4"],
                    "reference_audios": ["https://assets.example.test/reference.mp3"],
                },
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["status"], "queued")
        self.assertEqual(body["data"]["task_type"], "video_generate")
        self.assertIsInstance(body["data"]["task_id"], int)
        self.assertEqual(len(scheduled), 1)

        with self.SessionLocal() as db:
            task = db.scalar(select(GenerationTask).where(GenerationTask.id == body["data"]["task_id"]))
            self.assertIsNotNone(task)
            self.assertEqual(task.task_type, "video_generate")
            self.assertEqual(task.status, "queued")
            self.assertEqual(task.project_id, project_id)
            self.assertEqual(task.user_id, 1)
            self.assertEqual(task.input_data["prompt"], "jade bracelet video")
            self.assertEqual(task.input_data["reference_images"], ["https://assets.example.test/storyboard.png"])
            self.assertEqual(task.input_data["reference_videos"], ["https://assets.example.test/reference.mp4"])
            self.assertEqual(task.input_data["reference_audios"], ["https://assets.example.test/reference.mp3"])

        scheduled_args = scheduled[0]["args"]
        self.assertEqual(scheduled_args[3], 1)
        self.assertEqual(scheduled_args[9], ["https://assets.example.test/storyboard.png"])
        self.assertEqual(scheduled_args[10], ["https://assets.example.test/reference.mp4"])
        self.assertEqual(scheduled_args[11], ["https://assets.example.test/reference.mp3"])

    def test_generate_video_async_uploads_inline_reference_media_before_queue(self) -> None:
        scheduled = []
        project_id = self.create_project(self.client)
        image_data_url = "data:image/png;base64," + base64.b64encode(b"image-bytes").decode("ascii")
        uploaded_urls = []

        def fake_add_task(func, *args, **kwargs):
            scheduled.append({"func": func, "args": args, "kwargs": kwargs})

        def fake_upload_bytes(*, object_key, content, content_type, settings=None):
            uploaded_urls.append((object_key, content, content_type))
            return object_key

        with (
            patch("fastapi.BackgroundTasks.add_task", side_effect=fake_add_task),
            patch("app.api.video_generation.storage_service.is_oss_configured", return_value=True),
            patch(
                "app.api.video_generation.storage_service.build_reference_media_object_key",
                return_value="users/1/projects/1/references/images/test.png",
            ),
            patch("app.api.video_generation.storage_service.upload_bytes", side_effect=fake_upload_bytes),
            patch(
                "app.api.video_generation.storage_service.sign_get_url",
                return_value=("https://oss.example.test/reference.png", 999999),
            ),
        ):
            response = self.client.post(
                "/api/creation/videos/generate/async",
                json={
                    "project_id": project_id,
                    "prompt": "jade bracelet video",
                    "options": {"ratio": "9:16", "resolution": "720p"},
                    "first_frame": image_data_url,
                    "reference_images": [image_data_url],
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(uploaded_urls), 2)
        self.assertEqual(uploaded_urls[0][1], b"image-bytes")
        self.assertEqual(uploaded_urls[0][2], "image/png")

        with self.SessionLocal() as db:
            task_id = response.json()["data"]["task_id"]
            task = db.scalar(select(GenerationTask).where(GenerationTask.id == task_id))
            self.assertIsNotNone(task)
            self.assertEqual(task.input_data["first_frame"], "https://oss.example.test/reference.png")
            self.assertEqual(task.input_data["reference_images"], ["https://oss.example.test/reference.png"])

        scheduled_args = scheduled[0]["args"]
        self.assertEqual(scheduled_args[5], "https://oss.example.test/reference.png")
        self.assertEqual(scheduled_args[9], ["https://oss.example.test/reference.png"])

    def test_generate_video_async_rejects_inline_reference_media_without_oss(self) -> None:
        scheduled = []
        project_id = self.create_project(self.client)
        image_data_url = "data:image/png;base64," + base64.b64encode(b"image-bytes").decode("ascii")

        def fake_add_task(func, *args, **kwargs):
            scheduled.append({"func": func, "args": args, "kwargs": kwargs})

        with (
            patch("fastapi.BackgroundTasks.add_task", side_effect=fake_add_task),
            patch("app.api.video_generation.storage_service.is_oss_configured", return_value=False),
        ):
            response = self.client.post(
                "/api/creation/videos/generate/async",
                json={
                    "project_id": project_id,
                    "prompt": "jade bracelet video",
                    "first_frame": image_data_url,
                },
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn("OSS is required", response.json()["detail"])
        self.assertEqual(scheduled, [])

        with self.SessionLocal() as db:
            self.assertEqual(len(list(db.scalars(select(GenerationTask)).all())), 0)

    def test_generate_video_async_rejects_removed_endpoint_id_before_charge(self) -> None:
        scheduled = []
        project_id = self.create_project(self.client)

        def fake_add_task(func, *args, **kwargs):
            scheduled.append({"func": func, "args": args, "kwargs": kwargs})

        with patch("fastapi.BackgroundTasks.add_task", side_effect=fake_add_task):
            response = self.client.post(
                "/api/creation/videos/generate/async",
                json={
                    "project_id": project_id,
                    "prompt": "jade bracelet video",
                    "options": {
                        "model": "ep-m-20260415222504-8tt2k",
                        "resolution": "720p",
                        "duration_mode": "seconds",
                        "duration_seconds": 15,
                    },
                },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("不支持的视频模型", response.json()["detail"])
        self.assertEqual(scheduled, [])

        with self.SessionLocal() as db:
            self.assertEqual(len(list(db.scalars(select(GenerationTask)).all())), 0)

    def test_video_models_endpoint_returns_separate_seedance_endpoints(self) -> None:
        response = self.client.get("/api/creation/videos/models")

        self.assertEqual(response.status_code, 200)
        models = response.json()["data"]
        by_key = {item["key"]: item for item in models}

        self.assertEqual(by_key["seedance-2.0"]["value"], "doubao-seedance-2-0-260128")
        self.assertEqual(by_key["seedance-2.0"]["resolutions"], ["480p", "720p", "1080p"])
        self.assertTrue(by_key["seedance-2.0"]["available"])
        self.assertEqual(by_key["seedance-2.0-fast"]["value"], "doubao-seedance-2-0-fast-260128")
        self.assertEqual(by_key["seedance-2.0-fast"]["resolutions"], ["480p", "720p"])
        self.assertTrue(by_key["seedance-2.0-fast"]["available"])

    def test_video_result_creates_digital_asset_when_oss_is_not_configured(self) -> None:
        from app.api.video_generation import maybe_persist_video_to_oss

        project_id = self.create_project(self.client)

        with self.SessionLocal() as db, patch(
            "app.api.video_generation.storage_service.is_oss_configured",
            return_value=False,
        ):
            result = maybe_persist_video_to_oss(
                db,
                project_id,
                {
                    "provider": "seedance",
                    "model": "seedance-test",
                    "task_id": "provider-task-1",
                    "prompt": "jade bracelet video",
                    "video_url": "https://provider.example.test/video.mp4",
                },
                {"ratio": "9:16", "resolution": "1080p"},
                user_id=1,
            )

            asset = db.scalar(select(DigitalAsset).where(DigitalAsset.id == result["asset_id"]))
            self.assertIsNotNone(asset)
            self.assertEqual(asset.asset_type, "video")
            self.assertIsNone(asset.source_project_id)
            self.assertEqual(asset.project_snapshot["scope"], "account")
            self.assertEqual(asset.asset_metadata["source_project"]["project_id"], project_id)
            self.assertIsNone(asset.oss_object_key)
            self.assertEqual(asset.content_text, "jade bracelet video")
            self.assertEqual(asset.asset_metadata["prompt"], "jade bracelet video")
        self.assertEqual(asset.access_url, "https://provider.example.test/video.mp4")
        self.assertEqual(asset.asset_metadata["storage_status"], "oss_not_configured")

    def test_video_result_without_project_creates_account_asset_when_oss_is_not_configured(self) -> None:
        from app.api.video_generation import maybe_persist_video_to_oss

        with self.SessionLocal() as db, patch(
            "app.api.video_generation.storage_service.is_oss_configured",
            return_value=False,
        ):
            result = maybe_persist_video_to_oss(
                db,
                None,
                {
                    "provider": "seedance",
                    "model": "seedance-test",
                    "task_id": "provider-task-account",
                    "prompt": "account video",
                    "video_url": "https://provider.example.test/account-video.mp4",
                },
                {"ratio": "9:16", "resolution": "720p"},
                user_id=1,
            )

            asset = db.scalar(select(DigitalAsset).where(DigitalAsset.id == result["asset_id"]))
            self.assertIsNotNone(asset)
            self.assertEqual(asset.asset_type, "video")
            self.assertIsNone(asset.source_project_id)
            self.assertEqual(asset.project_snapshot["scope"], "account")
            self.assertEqual(asset.project_snapshot["project_name"], "账户资产")
            self.assertEqual(asset.user_id, 1)
            self.assertEqual(asset.access_url, "https://provider.example.test/account-video.mp4")
            self.assertEqual(asset.content_text, "account video")
            self.assertEqual(asset.asset_metadata["prompt"], "account video")
        self.assertEqual(asset.asset_metadata["storage_status"], "oss_not_configured")

    def test_fail_stale_generation_tasks_marks_only_old_active_tasks_failed(self) -> None:
        old_time = utcnow_naive() - timedelta(minutes=90)
        recent_time = utcnow_naive() - timedelta(minutes=5)
        with self.SessionLocal() as db:
            stale_running = GenerationTask(
                task_type="image_generate",
                status="running",
                user_id=1,
                project_id=7,
                input_data={"prompt": "old image"},
                updated_at=old_time,
            )
            fresh_running = GenerationTask(
                task_type="image_generate",
                status="running",
                user_id=1,
                project_id=7,
                input_data={"prompt": "fresh image"},
                updated_at=recent_time,
            )
            completed = GenerationTask(
                task_type="image_generate",
                status="succeeded",
                user_id=1,
                project_id=7,
                input_data={"prompt": "done image"},
                updated_at=old_time,
            )
            db.add_all([stale_running, fresh_running, completed])
            db.commit()

            changed = fail_stale_generation_tasks(db, max_age_minutes=60)

            self.assertEqual(changed, 1)
            self.assertEqual(stale_running.status, "failed")
            self.assertIn("重新生成", stale_running.error_message)
            self.assertEqual(fresh_running.status, "running")
            self.assertEqual(completed.status, "succeeded")

    def test_video_generation_task_persists_provider_task_id_while_running(self) -> None:
        from app.api.video_generation import run_video_generation_task

        with self.SessionLocal() as db:
            task = GenerationTask(
                task_type="video_generate",
                status="queued",
                user_id=1,
                project_id=7,
                input_data={"prompt": "jade video"},
            )
            db.add(task)
            db.commit()
            task_id = task.id

        def fake_generate_video(*args, on_provider_task_created=None, **kwargs):
            self.assertIsNotNone(on_provider_task_created)
            on_provider_task_created(
                {
                    "provider": "seedance",
                    "model": "seedance-test",
                    "task_id": "cgt-test-1",
                    "status": "submitted",
                }
            )
            with self.SessionLocal() as db:
                task = db.get(GenerationTask, task_id)
                self.assertEqual(task.status, "running")
                self.assertEqual(task.result_data["task_id"], "cgt-test-1")
                self.assertEqual(task.result_data["status"], "submitted")

            return {
                "provider": "seedance",
                "model": "seedance-test",
                "task_id": "cgt-test-1",
                "status": "succeeded",
                "video_url": "https://provider.example.test/video.mp4",
            }

        def fake_persist_video_to_oss(db, project_id, result, options, *, user_id):
            self.assertEqual(user_id, 1)
            return result

        with (
            patch("app.api.video_generation.SessionLocal", self.SessionLocal),
            patch("app.api.video_generation.video_generation_service.generate_video", side_effect=fake_generate_video),
            patch("app.api.video_generation.maybe_persist_video_to_oss", side_effect=fake_persist_video_to_oss),
        ):
            run_video_generation_task(task_id, "jade video", 7, 1, {"ratio": "16:9"})

        with self.SessionLocal() as db:
            task = db.get(GenerationTask, task_id)
            self.assertEqual(task.status, "succeeded")
            self.assertEqual(task.result_data["task_id"], "cgt-test-1")

    def test_video_generation_sends_requested_resolution_to_provider(self) -> None:
        from app.core.config import Settings
        from app.services import video_generation_service

        posted = {}

        def fake_post(endpoint, *, headers, json, timeout):
            posted["json"] = json
            return type(
                "Response",
                (),
                {
                    "status_code": 200,
                    "raise_for_status": lambda self: None,
                    "json": lambda self: {"id": "cgt-test-resolution"},
                },
            )()

        def fake_poll(*args, **kwargs):
            return {"status": "succeeded", "video_url": "https://provider.example.test/video.mp4", "raw_response": {}}

        settings = Settings(
            VIDEO_GENERATION_BASE_URL="https://ark.example.test",
            VIDEO_GENERATION_API_KEY="video-key",
            VIDEO_GENERATION_MODEL="seedance-test",
        )

        with (
            patch("app.services.video_generation_service.get_settings", return_value=settings),
            patch("app.services.video_generation_service.post_video_request_with_retry", side_effect=fake_post),
            patch("app.services.video_generation_service.poll_video_task", side_effect=fake_poll),
        ):
            video_generation_service.generate_video(
                "jade video",
                {
                    "model": "seedance-test",
                    "ratio": "16:9",
                    "resolution": "480p",
                    "duration_mode": "seconds",
                    "duration_seconds": 15,
                },
            )

        self.assertEqual(posted["json"]["resolution"], "480p")

    def test_recover_video_generation_task_persists_completed_provider_result(self) -> None:
        from app.api.video_generation import recover_interrupted_video_generation_tasks

        with self.SessionLocal() as db:
            task = GenerationTask(
                task_type="video_generate",
                status="running",
                user_id=1,
                project_id=7,
                input_data={
                    "prompt": "jade video",
                    "options": {"ratio": "16:9", "resolution": "480p"},
                },
                result_data={
                    "provider": "seedance",
                    "model": "seedance-test",
                    "task_id": "cgt-test-1",
                    "status": "submitted",
                },
            )
            db.add(task)
            db.commit()
            task_id = task.id

        def fake_get_video_task_result(task_id, db=None):
            self.assertEqual(task_id, "cgt-test-1")
            self.assertIsNotNone(db)
            return {
                "status": "succeeded",
                "video_url": "https://provider.example.test/video.mp4",
                "raw_response": {"status": "succeeded"},
            }

        def fake_persist_video_to_oss(db, project_id, result, options, *, user_id):
            self.assertEqual(project_id, 7)
            self.assertEqual(user_id, 1)
            self.assertEqual(result["task_id"], "cgt-test-1")
            self.assertEqual(result["prompt"], "jade video")
            result["asset_id"] = 123
            return result

        with (
            patch("app.api.video_generation.SessionLocal", self.SessionLocal),
            patch("app.api.video_generation.video_generation_service.get_video_task_result", side_effect=fake_get_video_task_result),
            patch("app.api.video_generation.maybe_persist_video_to_oss", side_effect=fake_persist_video_to_oss),
        ):
            recovered = recover_interrupted_video_generation_tasks()

        self.assertEqual(recovered, 1)
        with self.SessionLocal() as db:
            task = db.get(GenerationTask, task_id)
            self.assertEqual(task.status, "succeeded")
            self.assertEqual(task.result_data["task_id"], "cgt-test-1")
            self.assertEqual(task.result_data["video_url"], "https://provider.example.test/video.mp4")
            self.assertEqual(task.result_data["asset_id"], 123)


if __name__ == "__main__":
    unittest.main()
