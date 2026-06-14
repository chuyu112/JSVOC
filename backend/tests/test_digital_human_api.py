import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import auth_account  # noqa: F401
from app.models import credit  # noqa: F401
from app.models import digital_human_avatar  # noqa: F401
from app.models import digital_human_video  # noqa: F401
from app.models import digital_human_voice  # noqa: F401
from app.models import generation_task  # noqa: F401
from app.models import project  # noqa: F401
from app.models import script  # noqa: F401
from app.models import topic  # noqa: F401
from app.models import user  # noqa: F401
from app.models.digital_human_avatar import DigitalHumanAvatar
from app.models.digital_human_voice import DigitalHumanVoice
from app.models.project import Project
from app.models.script import Script
from app.models.topic import Topic


class DigitalHumanApiTest(unittest.TestCase):
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
        self.owner_client = TestClient(app)
        self.other_client = TestClient(app)
        self.owner_user_id = self.register_user(self.owner_client, "owner", "owner@example.com")
        self.other_user_id = self.register_user(self.other_client, "other", "other@example.com")

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

    def create_script_for_user(self, user_id: int, title: str) -> tuple[int, int]:
        with self.SessionLocal() as db:
            project = Project(
                user_id=user_id,
                project_name=f"{title} project",
                industry="jewelry",
                sub_industry="jade",
                product="jade bracelet",
                personal_intro="seller",
                target_audience="buyers",
                platforms=["douyin"],
                current_stage="stable",
            )
            db.add(project)
            db.flush()
            topic = Topic(
                project_id=project.id,
                title=f"{title} topic",
                content_type="tips",
                platform="douyin",
                goal="lead",
                topic_data={},
            )
            db.add(topic)
            db.flush()
            script = Script(
                project_id=project.id,
                topic_id=topic.id,
                title=f"{title} script",
                script_type="short",
                platform="douyin",
                script_content=f"{title} script content",
                shot_suggestions=[],
                conversion_script="dm me",
                script_data={},
            )
            db.add(script)
            db.commit()
            return project.id, script.id

    def create_avatar_and_voice(self, *, voice_user_id: int | None = None) -> tuple[int, int]:
        with self.SessionLocal() as db:
            avatar = DigitalHumanAvatar(name="Preset avatar", avatar_type="preset", is_active=True)
            voice = DigitalHumanVoice(
                user_id=voice_user_id,
                name="Voice",
                voice_type="preset" if voice_user_id is None else "cloned",
                is_active=True,
            )
            db.add_all([avatar, voice])
            db.commit()
            return avatar.id, voice.id

    def test_generate_rejects_script_from_another_user(self) -> None:
        owner_project_id, owner_script_id = self.create_script_for_user(self.owner_user_id, "owner")
        avatar_id, voice_id = self.create_avatar_and_voice()

        with patch("fastapi.BackgroundTasks.add_task") as add_task:
            response = self.other_client.post(
                "/api/digital-human/videos/generate",
                json={
                    "project_id": owner_project_id,
                    "script_id": owner_script_id,
                    "avatar_id": avatar_id,
                    "voice_id": voice_id,
                },
            )

        self.assertEqual(response.status_code, 404)
        add_task.assert_not_called()

    def test_generate_rejects_cloned_voice_from_another_user(self) -> None:
        other_project_id, other_script_id = self.create_script_for_user(self.other_user_id, "other")
        avatar_id, owner_voice_id = self.create_avatar_and_voice(voice_user_id=self.owner_user_id)

        with patch("fastapi.BackgroundTasks.add_task") as add_task:
            response = self.other_client.post(
                "/api/digital-human/videos/generate",
                json={
                    "project_id": other_project_id,
                    "script_id": other_script_id,
                    "avatar_id": avatar_id,
                    "voice_id": owner_voice_id,
                },
            )

        self.assertEqual(response.status_code, 404)
        add_task.assert_not_called()


if __name__ == "__main__":
    unittest.main()
