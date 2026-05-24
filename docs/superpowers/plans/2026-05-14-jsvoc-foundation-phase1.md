# JSVOC Foundation Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first real authentication foundation and change project editing to update in place instead of creating a new project version.

**Architecture:** This phase introduces a dedicated user domain with `users` and `auth_accounts`, plus cookie-based session endpoints for register/login/logout/me. It does not yet hard-gate every existing business route; instead it establishes the data model and API surface needed for later ownership enforcement while safely correcting project update semantics now.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, unittest, browser cookie sessions

---

### Task 1: Add failing tests for authentication and in-place project updates

**Files:**
- Create: `backend/tests/test_auth_api.py`
- Modify: `backend/tests/test_projects_api.py`

- [ ] **Step 1: Write the failing auth test file**

```python
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

        me_response = self.client.get("/api/auth/me")
        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.json()["data"]["user"]["username"], "alice")

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
```

- [ ] **Step 2: Write the new in-place project update expectation**

```python
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
        self.assertEqual(updated_project["product"], "jade pendant")

        self.assertEqual(self.count_for_project(Topic, original_project_id), 1)
        self.assertEqual(self.count_for_project(Script, original_project_id), 1)
        self.assertEqual(self.count_for_project(AccountStrategyContext, original_project_id), 1)
        self.assertEqual(self.count_for_project(GenerationRecord, original_project_id), 1)
```

- [ ] **Step 3: Run the focused tests to verify they fail**

Run:

```powershell
cd backend
python -m unittest tests.test_auth_api tests.test_projects_api -v
```

Expected:

- `test_register_login_me_and_logout_flow` fails with 404 because auth routes do not exist yet
- project update test fails because the API still creates a new project id

### Task 2: Implement user/auth data model and migration

**Files:**
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/auth_account.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/db/base.py`
- Create: `backend/alembic/versions/20260514_0004_add_users_and_auth_accounts.py`

- [ ] **Step 1: Add the user model**

```python
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
```

- [ ] **Step 2: Add the auth account model**

```python
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuthAccount(Base):
    __tablename__ = "auth_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    provider_key: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
```

- [ ] **Step 3: Register the models**

```python
from app.models.account_strategy_context import AccountStrategyContext
from app.models.auth_account import AuthAccount
from app.models.generation_record import GenerationRecord
from app.models.generation_task import GenerationTask
from app.models.project import Project
from app.models.script import Script
from app.models.topic import Topic
from app.models.user import User

__all__ = [
    "AccountStrategyContext",
    "AuthAccount",
    "GenerationRecord",
    "GenerationTask",
    "Project",
    "Script",
    "Topic",
    "User",
]
```

- [ ] **Step 4: Add the Alembic migration**

```python
def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)

    op.create_table(
        "auth_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider_type", sa.String(length=40), nullable=False),
        sa.Column("provider_key", sa.String(length=200), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_auth_accounts_id"), "auth_accounts", ["id"], unique=False)
    op.create_index(op.f("ix_auth_accounts_provider_key"), "auth_accounts", ["provider_key"], unique=False)
    op.create_index(op.f("ix_auth_accounts_provider_type"), "auth_accounts", ["provider_type"], unique=False)
    op.create_index(op.f("ix_auth_accounts_user_id"), "auth_accounts", ["user_id"], unique=False)
```

- [ ] **Step 5: Run migration and model tests**

Run:

```powershell
cd backend
python -m unittest tests.test_alembic_migrations -v
```

Expected: PASS and new tables appear in migration head.

### Task 3: Implement auth schemas, service, and routes

**Files:**
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/services/auth_service.py`
- Create: `backend/app/api/auth.py`
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Add auth settings**

```python
    auth_secret_key: str = Field(default="jsvoc-dev-secret", alias="AUTH_SECRET_KEY")
    auth_cookie_name: str = Field(default="jsvoc_session", alias="AUTH_COOKIE_NAME")
    auth_session_ttl_seconds: int = Field(default=604800, alias="AUTH_SESSION_TTL_SECONDS", gt=0)
```

- [ ] **Step 2: Add auth schemas**

```python
class RegisterRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    username: str = Field(min_length=3, max_length=60)
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=8, max_length=200)


class LoginRequest(BaseModel):
    login: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=8, max_length=200)
```

- [ ] **Step 3: Add auth service**

```python
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000)
    return f"{salt}${derived.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    salt, expected = password_hash.split("$", 1)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000)
    return hmac.compare_digest(derived.hex(), expected)
```

- [ ] **Step 4: Add auth routes**

```python
@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(...)

@router.post("/login")
def login(...)

@router.post("/logout")
def logout(...)

@router.get("/me")
def me(...)
```

- [ ] **Step 5: Register the router**

```python
from app.api.auth import router as auth_router

app.include_router(auth_router)
```

- [ ] **Step 6: Run the auth tests to verify they pass**

Run:

```powershell
cd backend
python -m unittest tests.test_auth_api -v
```

Expected: PASS

### Task 4: Change project update semantics to edit in place

**Files:**
- Modify: `backend/app/services/project_service.py`
- Test: `backend/tests/test_projects_api.py`

- [ ] **Step 1: Replace clone-on-update with in-place mutation**

```python
def update_project(db: Session, project: Project, project_in: ProjectUpdate) -> Project:
    update_data = project_in.model_dump(exclude_unset=True)
    if not update_data:
        return project

    for field, value in update_data.items():
        setattr(project, field, value)

    db.add(project)
    db.commit()
    db.refresh(project)
    return project
```

- [ ] **Step 2: Rename the test in `test_projects_api.py` to reflect new behavior**

```python
def test_updating_project_edits_same_record_and_keeps_generated_data(self) -> None:
```

- [ ] **Step 3: Run the project tests**

Run:

```powershell
cd backend
python -m unittest tests.test_projects_api -v
```

Expected: PASS

### Task 5: Run regression verification for Phase 1

**Files:**
- Test: `backend/tests/test_auth_api.py`
- Test: `backend/tests/test_projects_api.py`
- Test: `backend/tests/test_alembic_migrations.py`

- [ ] **Step 1: Run the focused phase suite**

Run:

```powershell
cd backend
python -m unittest tests.test_auth_api tests.test_projects_api tests.test_alembic_migrations -v
```

Expected: PASS

- [ ] **Step 2: Run the full backend suite**

Run:

```powershell
cd backend
python -m unittest discover -s tests -v
```

Expected: PASS
