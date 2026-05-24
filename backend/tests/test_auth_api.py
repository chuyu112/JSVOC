import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import project  # noqa: F401


class AuthApiTest(unittest.TestCase):
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

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_register_login_me_and_logout_flow(self) -> None:
        register_response = self.client.post(
            "/api/auth/register",
            json={
                "display_name": "Alice",
                "username": "alice",
                "email": "alice@example.com",
                "password": "StrongPass123",
            },
        )
        self.assertEqual(register_response.status_code, 201)
        self.assertEqual(register_response.json()["data"]["user"]["display_name"], "Alice")
        self.assertEqual(register_response.json()["data"]["user"]["credit_balance"], 2000)

        me_response = self.client.get("/api/auth/me")
        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.json()["data"]["user"]["username"], "alice")
        self.assertEqual(me_response.json()["data"]["user"]["credit_balance"], 2000)

        logout_response = self.client.post("/api/auth/logout")
        self.assertEqual(logout_response.status_code, 200)

        me_after_logout = self.client.get("/api/auth/me")
        self.assertEqual(me_after_logout.status_code, 401)

        login_response = self.client.post(
            "/api/auth/login",
            json={"login": "alice@example.com", "password": "StrongPass123"},
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(login_response.json()["data"]["user"]["email"], "alice@example.com")

    def test_register_accepts_chinese_username(self) -> None:
        register_response = self.client.post(
            "/api/auth/register",
            json={
                "display_name": "chuyu111",
                "username": "刘峥",
                "email": "liuzheng@example.com",
                "password": "StrongPass123",
            },
        )

        self.assertEqual(register_response.status_code, 201)
        self.assertEqual(register_response.json()["data"]["user"]["username"], "刘峥")

        login_response = self.client.post(
            "/api/auth/login",
            json={"login": "刘峥", "password": "StrongPass123"},
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(login_response.json()["data"]["user"]["email"], "liuzheng@example.com")


if __name__ == "__main__":
    unittest.main()
