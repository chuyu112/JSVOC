import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import account_strategy_context  # noqa: F401
from app.models import generation_record  # noqa: F401
from app.models import project  # noqa: F401
from app.models import script  # noqa: F401
from app.models import topic  # noqa: F401
from app.models.account_strategy_context import AccountStrategyContext
from app.models.generation_record import GenerationRecord
from app.models.script import Script
from app.models.topic import Topic


class ProjectsApiTest(unittest.TestCase):
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
        self.register_user(self.client, "owner", "owner@example.com")

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def create_project(self) -> int:
        response = self.client.post(
            "/api/projects",
            json={
                "project_name": "jade account",
                "industry": "jewelry",
                "sub_industry": "jade",
                "product": "jade bracelet",
                "personal_intro": "20 years jade seller",
                "target_audience": "city gift buyers",
                "platforms": ["douyin"],
                "current_stage": "stable",
            },
        )
        return response.json()["data"]["id"]

    def register_user(self, client: TestClient, username: str, email: str) -> None:
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

    def add_generated_data(self, project_id: int) -> None:
        with self.SessionLocal() as db:
            topic = Topic(
                project_id=project_id,
                title="old topic",
                content_type="tips",
                platform="douyin",
                goal="lead",
                score=90,
                topic_data={},
            )
            db.add(topic)
            db.flush()
            db.add(
                Script(
                    project_id=project_id,
                    topic_id=topic.id,
                    title="old script",
                    script_type="short",
                    platform="douyin",
                    script_content="old script content",
                    shot_suggestions=[],
                    conversion_script="old conversion",
                    script_data={},
                )
            )
            db.add(
                AccountStrategyContext(
                    project_id=project_id,
                    account_positioning="old positioning",
                    persona="old persona",
                    target_user_profile={},
                    account_names=[],
                    bios={},
                    content_columns=[],
                    trust_design=[],
                    conversion_path=[],
                    platform_strategies={},
                    trust_points=[],
                    monetization_paths=[],
                    context_data={},
                )
            )
            db.add(
                GenerationRecord(
                    project_id=project_id,
                    module_name="execution_plan",
                    input_data={},
                    output_data={},
                    model_provider="mock",
                    model_name="mock",
                    token_usage={},
                )
            )
            db.commit()

    def count_for_project(self, model, project_id: int) -> int:
        with self.SessionLocal() as db:
            return db.scalar(select(func.count()).select_from(model).where(model.project_id == project_id))

    def test_updating_project_edits_same_record_and_keeps_generated_data(self) -> None:
        original_project_id = self.create_project()
        self.add_generated_data(original_project_id)

        response = self.client.put(
            f"/api/projects/{original_project_id}",
            json={
                "project_name": "jade account revised",
                "industry": "jewelry",
                "sub_industry": "jade",
                "product": "jade pendant",
                "personal_intro": "20 years jade seller",
                "target_audience": "city gift buyers",
                "platforms": ["douyin"],
                "current_stage": "stable",
            },
        )

        self.assertEqual(response.status_code, 200)
        updated_project = response.json()["data"]
        self.assertEqual(updated_project["id"], original_project_id)
        self.assertEqual(updated_project["industry"], "珠宝")
        self.assertEqual(updated_project["sub_industry"], "翡翠")
        self.assertEqual(updated_project["product"], "jade pendant")

        self.assertEqual(self.count_for_project(Topic, original_project_id), 1)
        self.assertEqual(self.count_for_project(Script, original_project_id), 1)
        self.assertEqual(self.count_for_project(AccountStrategyContext, original_project_id), 1)
        self.assertEqual(self.count_for_project(GenerationRecord, original_project_id), 1)

    def test_project_listing_and_lookup_are_scoped_to_current_user(self) -> None:
        owner_project_id = self.create_project()

        other_client = TestClient(app)
        self.register_user(other_client, "other", "other@example.com")
        create_response = other_client.post(
            "/api/projects",
            json={
                "project_name": "other project",
                "industry": "jewelry",
                "sub_industry": "jade",
                "product": "jade pendant",
                "personal_intro": "other seller",
                "target_audience": "other buyers",
                "platforms": ["douyin"],
                "current_stage": "stable",
            },
        )
        self.assertEqual(create_response.status_code, 201)

        owner_list = self.client.get("/api/projects")
        self.assertEqual(owner_list.status_code, 200)
        self.assertEqual(len(owner_list.json()["data"]), 1)
        self.assertEqual(owner_list.json()["data"][0]["id"], owner_project_id)

        hidden_response = other_client.get(f"/api/projects/{owner_project_id}")
        self.assertEqual(hidden_response.status_code, 404)


    def test_project_industry_is_forced_to_jewelry_jade(self) -> None:
        create_response = self.client.post(
            '/api/projects',
            json={
                'project_name': 'locked industry',
                'industry': '餐饮',
                'sub_industry': '咖啡',
                'product': 'jade pendant',
                'personal_intro': 'seller',
                'target_audience': 'buyers',
                'platforms': ['douyin'],
                'current_stage': 'stable',
            },
        )
        self.assertEqual(create_response.status_code, 201)
        project = create_response.json()['data']
        self.assertEqual(project['industry'], '珠宝')
        self.assertEqual(project['sub_industry'], '翡翠')
        project_id = project['id']

        update_response = self.client.put(
            f'/api/projects/{project_id}',
            json={'industry': '教育', 'sub_industry': '培训'},
        )
        self.assertEqual(update_response.status_code, 200)
        updated_project = update_response.json()['data']
        self.assertEqual(updated_project['industry'], '珠宝')
        self.assertEqual(updated_project['sub_industry'], '翡翠')


if __name__ == "__main__":
    unittest.main()
