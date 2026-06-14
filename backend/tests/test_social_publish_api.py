import tempfile
import unittest
from pathlib import Path
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
from app.models import digital_asset  # noqa: F401
from app.models import project  # noqa: F401
from app.models import user  # noqa: F401


class SocialPublishApiTest(unittest.TestCase):
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
        self.register_user("owner", "owner@example.com")

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

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

    def test_publish_rejects_arbitrary_server_file_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            video_path = Path(tmp_dir) / "private.mp4"
            video_path.write_bytes(b"video")

            with patch("app.api.social_publish.SocialPublishService") as service_class:
                response = self.client.post(
                    "/api/social-publish/publish",
                    json={
                        "video_url": str(video_path),
                        "title": "do not publish",
                        "platforms": ["douyin"],
                    },
                )

        self.assertEqual(response.status_code, 400)
        service_class.return_value.publish.assert_not_called()


if __name__ == "__main__":
    unittest.main()
