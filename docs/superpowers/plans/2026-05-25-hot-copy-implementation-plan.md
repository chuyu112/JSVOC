# Hot Copy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first Douyin-focused hot-copy workflow: manual viral script entry, AI structure analysis, AI rewrite, generation history, and a reserved Redianbao search entry.

**Architecture:** Backend owns storage, auth scoping, validation, LLM Gateway calls, credit charging, and generation records. Frontend adds a `/hot-copy` workbench where users paste Douyin material, analyze it, rewrite it, and send the generated script into the existing video workflow. Redianbao is represented by a real API/UI entry that returns a clear not-connected result.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, PostgreSQL/SQLite tests, unittest/TestClient, Next.js App Router, TypeScript, React, existing `api` helper, Node built-in tests, gstack browser QA.

---

## File Structure

Backend:

- Create `backend/app/models/hot_copy.py`: `HotCopyMaterial` and `HotCopyRewrite` SQLAlchemy models.
- Modify `backend/app/models/__init__.py`: export the two models.
- Modify `backend/app/db/base.py`: import the model module inside `init_db`.
- Create `backend/alembic/versions/20260525_0013_add_hot_copy_tables.py`: database migration after `20260524_0012`.
- Create `backend/app/schemas/hot_copy.py`: request and response schemas.
- Create `backend/app/prompts/hot_copy_prompt.py`: prompt builders, module names, prompt versions, and JSON output schemas.
- Create `backend/app/services/hot_copy_service.py`: material CRUD, analysis, rewrite, Redianbao reserved response, credit charging.
- Create `backend/app/api/hot_copy.py`: `/api/hot-copy/*` routes.
- Modify `backend/app/main.py`: include the new router.
- Modify `backend/app/llm/llm_gateway.py`: add mock data for `hot_copy_analysis` and `hot_copy_rewrite` before the generic copy/script branch.
- Modify `backend/tests/test_alembic_migrations.py`: migration coverage.
- Create `backend/tests/test_hot_copy_api.py`: API, ownership, history, and Redianbao tests.

Frontend:

- Create `frontend-v2/src/lib/api/hotCopy.ts`: typed API helper.
- Modify `frontend-v2/src/lib/api/generationRecords.ts`: add hot-copy modules to type union and labels.
- Modify `frontend-v2/src/app/history/HistoryClient.tsx`: add hot-copy filters and tag styling.
- Modify `frontend-v2/src/components/AppShell.tsx`: add `/hot-copy` navigation item.
- Create `frontend-v2/src/app/hot-copy/page.tsx`: workbench UI.
- Modify `frontend-v2/src/app/globals.css`: exact small CSS additions for textarea/select behavior.
- Create `frontend-v2/tests/hotCopyEntry.test.ts`: route/nav/API source test.
- Create `frontend-v2/tests/hotCopyHistory.test.ts`: history module source test.
- Create `frontend-v2/tests/hotCopyPage.test.ts`: page source test.

---

### Task 1: Database Models And Migration

**Files:**
- Create: `backend/app/models/hot_copy.py`
- Create: `backend/alembic/versions/20260525_0013_add_hot_copy_tables.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/db/base.py`
- Modify: `backend/tests/test_alembic_migrations.py`

- [ ] **Step 1: Write the failing migration test**

In `backend/tests/test_alembic_migrations.py`, update the expected table set in `test_upgrade_head_creates_current_mvp_tables_on_sqlite`:

```python
self.assertEqual(
    {
        "account_strategy_contexts",
        "auth_accounts",
        "credit_accounts",
        "credit_transactions",
        "digital_assets",
        "generation_records",
        "generation_tasks",
        "hot_copy_materials",
        "hot_copy_rewrites",
        "llm_channels",
        "projects",
        "project_reference_images",
        "scripts",
        "topics",
        "users",
    },
    set(inspector.get_table_names()) - {"alembic_version"},
)
```

Add these column assertions after the table assertion:

```python
material_columns = {column["name"] for column in inspector.get_columns("hot_copy_materials")}
self.assertTrue(
    {
        "id",
        "user_id",
        "project_id",
        "platform",
        "source_type",
        "source_url",
        "account_name",
        "account_home_url",
        "cover_url",
        "title",
        "original_script",
        "metrics_json",
        "analysis_json",
        "created_at",
        "updated_at",
    }.issubset(material_columns)
)
rewrite_columns = {column["name"] for column in inspector.get_columns("hot_copy_rewrites")}
self.assertTrue(
    {
        "id",
        "material_id",
        "user_id",
        "project_id",
        "rewrite_mode",
        "duration",
        "conversion_goal",
        "input_json",
        "output_json",
        "generation_record_id",
        "created_at",
    }.issubset(rewrite_columns)
)
```

- [ ] **Step 2: Run the migration test and confirm failure**

Run from `backend`:

```bash
python -m unittest tests.test_alembic_migrations
```

Expected: the test fails because `hot_copy_materials` and `hot_copy_rewrites` do not exist.

- [ ] **Step 3: Add SQLAlchemy models**

Create `backend/app/models/hot_copy.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.datetime_utils import utcnow_naive
from app.db.base import Base


class HotCopyMaterial(Base):
    __tablename__ = "hot_copy_materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    platform: Mapped[str] = mapped_column(String(40), nullable=False, default="douyin")
    source_type: Mapped[str] = mapped_column(String(40), nullable=False, default="manual", index=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    account_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    account_home_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    cover_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    original_script: Mapped[str] = mapped_column(Text, nullable=False)
    metrics_json: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), default=dict, nullable=False)
    analysis_json: Mapped[dict | None] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, onupdate=utcnow_naive, nullable=False)


class HotCopyRewrite(Base):
    __tablename__ = "hot_copy_rewrites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("hot_copy_materials.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    rewrite_mode: Mapped[str] = mapped_column(String(40), nullable=False)
    duration: Mapped[str] = mapped_column(String(20), nullable=False)
    conversion_goal: Mapped[str] = mapped_column(String(80), nullable=False)
    input_json: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), default=dict, nullable=False)
    output_json: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), default=dict, nullable=False)
    generation_record_id: Mapped[int | None] = mapped_column(
        ForeignKey("generation_records.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, nullable=False)
```

Modify `backend/app/models/__init__.py`:

```python
from app.models.hot_copy import HotCopyMaterial, HotCopyRewrite
```

Add `HotCopyMaterial` and `HotCopyRewrite` to `__all__`.

Modify `backend/app/db/base.py` inside `init_db()`:

```python
from app.models import hot_copy  # noqa: F401
```

- [ ] **Step 4: Add Alembic migration**

Create `backend/alembic/versions/20260525_0013_add_hot_copy_tables.py`:

```python
"""add hot copy tables

Revision ID: 20260525_0013
Revises: 20260524_0012
Create Date: 2026-05-25 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260525_0013"
down_revision = "20260524_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hot_copy_materials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("platform", sa.String(length=40), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("account_name", sa.String(length=120), nullable=True),
        sa.Column("account_home_url", sa.String(length=1000), nullable=True),
        sa.Column("cover_url", sa.String(length=1000), nullable=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("original_script", sa.Text(), nullable=False),
        sa.Column("metrics_json", sa.JSON(), nullable=False),
        sa.Column("analysis_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_hot_copy_materials_id"), "hot_copy_materials", ["id"], unique=False)
    op.create_index(op.f("ix_hot_copy_materials_user_id"), "hot_copy_materials", ["user_id"], unique=False)
    op.create_index(op.f("ix_hot_copy_materials_project_id"), "hot_copy_materials", ["project_id"], unique=False)
    op.create_index(op.f("ix_hot_copy_materials_source_type"), "hot_copy_materials", ["source_type"], unique=False)

    op.create_table(
        "hot_copy_rewrites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("material_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("rewrite_mode", sa.String(length=40), nullable=False),
        sa.Column("duration", sa.String(length=20), nullable=False),
        sa.Column("conversion_goal", sa.String(length=80), nullable=False),
        sa.Column("input_json", sa.JSON(), nullable=False),
        sa.Column("output_json", sa.JSON(), nullable=False),
        sa.Column("generation_record_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["generation_record_id"], ["generation_records.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["material_id"], ["hot_copy_materials.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_hot_copy_rewrites_id"), "hot_copy_rewrites", ["id"], unique=False)
    op.create_index(op.f("ix_hot_copy_rewrites_material_id"), "hot_copy_rewrites", ["material_id"], unique=False)
    op.create_index(op.f("ix_hot_copy_rewrites_user_id"), "hot_copy_rewrites", ["user_id"], unique=False)
    op.create_index(op.f("ix_hot_copy_rewrites_project_id"), "hot_copy_rewrites", ["project_id"], unique=False)
    op.create_index(op.f("ix_hot_copy_rewrites_generation_record_id"), "hot_copy_rewrites", ["generation_record_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_hot_copy_rewrites_generation_record_id"), table_name="hot_copy_rewrites")
    op.drop_index(op.f("ix_hot_copy_rewrites_project_id"), table_name="hot_copy_rewrites")
    op.drop_index(op.f("ix_hot_copy_rewrites_user_id"), table_name="hot_copy_rewrites")
    op.drop_index(op.f("ix_hot_copy_rewrites_material_id"), table_name="hot_copy_rewrites")
    op.drop_index(op.f("ix_hot_copy_rewrites_id"), table_name="hot_copy_rewrites")
    op.drop_table("hot_copy_rewrites")
    op.drop_index(op.f("ix_hot_copy_materials_source_type"), table_name="hot_copy_materials")
    op.drop_index(op.f("ix_hot_copy_materials_project_id"), table_name="hot_copy_materials")
    op.drop_index(op.f("ix_hot_copy_materials_user_id"), table_name="hot_copy_materials")
    op.drop_index(op.f("ix_hot_copy_materials_id"), table_name="hot_copy_materials")
    op.drop_table("hot_copy_materials")
```

- [ ] **Step 5: Run the migration test and confirm pass**

Run from `backend`:

```bash
python -m unittest tests.test_alembic_migrations
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/hot_copy.py backend/app/models/__init__.py backend/app/db/base.py backend/alembic/versions/20260525_0013_add_hot_copy_tables.py backend/tests/test_alembic_migrations.py
git commit -m "feat: add hot copy database tables"
```

---

### Task 2: Schemas, Prompts, And Mock LLM Output

**Files:**
- Create: `backend/app/schemas/hot_copy.py`
- Create: `backend/app/prompts/hot_copy_prompt.py`
- Modify: `backend/app/llm/llm_gateway.py`
- Test: `backend/tests/test_hot_copy_api.py`

- [ ] **Step 1: Add the first failing schema/API test**

Create `backend/tests/test_hot_copy_api.py` with this shared setup and one validation test:

```python
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import auth_account, credit, generation_record, hot_copy, llm_channel, project, user  # noqa: F401


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
        self.register_user("owner", "owner@example.com")

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
```

- [ ] **Step 2: Run the test and confirm failure**

Run from `backend`:

```bash
python -m unittest tests.test_hot_copy_api
```

Expected: route or import failure because the schema/API does not exist.

- [ ] **Step 3: Create Pydantic schemas**

Create `backend/app/schemas/hot_copy.py`:

```python
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


HotCopyPlatform = Literal["douyin"]
RewriteMode = Literal["light", "medium", "strong"]
RewriteDuration = Literal["30s", "60s", "90s"]


class HotCopyMaterialManualCreate(BaseModel):
    project_id: int | None = Field(default=None, gt=0)
    platform: HotCopyPlatform = "douyin"
    source_url: str | None = Field(default=None, max_length=1000)
    account_name: str | None = Field(default=None, max_length=120)
    account_home_url: str | None = Field(default=None, max_length=1000)
    cover_url: str | None = Field(default=None, max_length=1000)
    title: str = Field(min_length=1, max_length=240)
    original_script: str = Field(min_length=1, max_length=12000)
    metrics_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("title", "original_script")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be blank")
        return cleaned

    @field_validator("source_url", "account_name", "account_home_url", "cover_url")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class HotCopyMaterialRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    project_id: int | None
    platform: str
    source_type: str
    source_url: str | None
    account_name: str | None
    account_home_url: str | None
    cover_url: str | None
    title: str
    original_script: str
    metrics_json: dict[str, Any]
    analysis_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class HotCopyAnalysisResponse(BaseModel):
    material: HotCopyMaterialRead
    analysis: dict[str, Any]
    generation_record_id: int | None


class HotCopyRewriteRequest(BaseModel):
    project_id: int | None = Field(default=None, gt=0)
    rewrite_mode: RewriteMode = "medium"
    duration: RewriteDuration = "60s"
    conversion_goal: str = Field(default="私信获客", min_length=1, max_length=80)
    product: str | None = Field(default=None, max_length=200)
    target_customer: str | None = Field(default=None, max_length=300)
    account_persona: str | None = Field(default=None, max_length=300)

    @field_validator("conversion_goal")
    @classmethod
    def strip_conversion_goal(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be blank")
        return cleaned


class HotCopyRewriteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    material_id: int
    user_id: int
    project_id: int | None
    rewrite_mode: str
    duration: str
    conversion_goal: str
    input_json: dict[str, Any]
    output_json: dict[str, Any]
    generation_record_id: int | None
    created_at: datetime


class HotCopyRewriteResponse(BaseModel):
    rewrite: HotCopyRewriteRead
    output: dict[str, Any]
    generation_record_id: int | None


class HotCopyRedianbaoSearchRequest(BaseModel):
    keyword: str = Field(min_length=1, max_length=120)
    platform: HotCopyPlatform = "douyin"
    count: int = Field(default=30, ge=30, le=100)
```

- [ ] **Step 4: Create prompt builders**

Create `backend/app/prompts/hot_copy_prompt.py`:

```python
from app.models.hot_copy import HotCopyMaterial
from app.models.project import Project
from app.schemas.hot_copy import HotCopyRewriteRequest


HOT_COPY_ANALYSIS_MODULE = "hot_copy_analysis"
HOT_COPY_REWRITE_MODULE = "hot_copy_rewrite"
HOT_COPY_ANALYSIS_PROMPT_VERSION = "hot-copy-analysis-v1"
HOT_COPY_REWRITE_PROMPT_VERSION = "hot-copy-rewrite-v1"

HOT_COPY_ANALYSIS_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["hook", "structure", "emotion_triggers", "trust_builders", "conversion_points", "risk_notes"],
    "properties": {
        "hook": {"type": "string"},
        "structure": {"type": "array", "items": {"type": "string"}},
        "emotion_triggers": {"type": "array", "items": {"type": "string"}},
        "trust_builders": {"type": "array", "items": {"type": "string"}},
        "conversion_points": {"type": "array", "items": {"type": "string"}},
        "risk_notes": {"type": "array", "items": {"type": "string"}},
        "rewrite_brief": {"type": "string"},
    },
}

HOT_COPY_REWRITE_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["title", "hook", "script", "shot_suggestions", "conversion_script", "risk_notes"],
    "properties": {
        "title": {"type": "string"},
        "hook": {"type": "string"},
        "script": {"type": "string"},
        "shot_suggestions": {"type": "array", "items": {"type": "string"}},
        "conversion_script": {"type": "string"},
        "risk_notes": {"type": "array", "items": {"type": "string"}},
    },
}


def build_hot_copy_analysis_prompts(material: HotCopyMaterial) -> tuple[str, str]:
    system_prompt = (
        "你是短视频口播爆款拆解专家。只输出符合 JSON Schema 的 JSON，"
        "不要照搬原文，不要提供搬运建议。"
    )
    user_prompt = f"""
平台：抖音
来源账号：{material.account_name or "未填写"}
标题：{material.title}
公开指标：{material.metrics_json}
原始口播文案：
{material.original_script}

请拆解这条口播为什么容易爆，输出开头钩子、内容结构、情绪触发、信任背书、转化点、风险提醒和仿写简报。
"""
    return system_prompt, user_prompt.strip()


def build_hot_copy_rewrite_prompts(
    material: HotCopyMaterial,
    project: Project | None,
    payload: HotCopyRewriteRequest,
) -> tuple[str, str]:
    system_prompt = (
        "你是短视频账号文案策划。基于爆款结构重写，不复刻原文表达。"
        "输出必须是 JSON，适合真人口播和后续一键生成视频。"
    )
    project_context = "未绑定项目"
    if project is not None:
        project_context = (
            f"行业：{project.industry}\n产品/服务：{project.product}\n"
            f"个人简介：{project.personal_intro}\n目标客户：{project.target_audience}"
        )
    user_prompt = f"""
平台：抖音
仿写强度：{payload.rewrite_mode}
目标时长：{payload.duration}
转化目标：{payload.conversion_goal}
补充产品：{payload.product or ""}
补充客户：{payload.target_customer or ""}
补充人设：{payload.account_persona or ""}

项目上下文：
{project_context}

原始标题：{material.title}
原始口播：
{material.original_script}

已拆解结构：
{material.analysis_json or {}}

请生成一条新的口播文案，包含标题、开头钩子、完整口播、拍摄建议、转化话术和风险提醒。
"""
    return system_prompt, user_prompt.strip()
```

- [ ] **Step 5: Add mock output to LLM Gateway**

In `backend/app/llm/llm_gateway.py`, add these branches inside `_mock_data_for_module` before the existing generic `"script" in normalized or "copy" in normalized` branch:

```python
if normalized == "hot_copy_analysis":
    return self._mock_hot_copy_analysis(metadata or {})
if normalized == "hot_copy_rewrite":
    return self._mock_hot_copy_rewrite(metadata or {})
```

Add these methods near `_mock_hot_video_search`:

```python
def _mock_hot_copy_analysis(self, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    title = str((metadata or {}).get("title") or "新手买翡翠别先问最低价")
    return {
        "hook": f"{title} 用反常识开场，直接拦住新手的错误动作。",
        "structure": ["反常识提醒", "提出三步判断", "展示信任经验", "引导私信承接"],
        "emotion_triggers": ["怕踩坑", "怕买贵", "想找懂行的人先看"],
        "trust_builders": ["源头市场经验", "实物细节判断", "明确不让用户冲动下单"],
        "conversion_points": ["评论预算", "私信用途", "发送实物图"],
        "risk_notes": ["不要照搬原作者原句", "不要使用原视频画面"],
        "rewrite_brief": "重写时保留反常识开头和三步判断结构，换成自己的产品、人设和转化动作。",
    }


def _mock_hot_copy_rewrite(self, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    metadata = metadata or {}
    product = str(metadata.get("product") or "翡翠手镯")
    duration = str(metadata.get("duration") or "60s")
    return {
        "title": f"买{product}别先问最低价",
        "hook": f"买{product}，你一上来就问最低价，很容易被带着走。",
        "script": (
            f"今天用{duration}讲一个新手最容易踩的坑。买{product}别先问最低价，先看三件事。"
            "第一，看自然光下整体干不干净；第二，看纹裂棉有没有影响佩戴；"
            "第三，把预算、用途和款式放在一起判断。"
            "如果你只是日常戴，不一定追求最冰最透，稳定耐看更重要。"
            "想让我帮你先看方向，可以在评论区说预算和用途，或者私信发图。"
        ),
        "shot_suggestions": ["真人开场提出误区", "展示产品自然光细节", "用字幕列出三步判断", "结尾引导评论或私信"],
        "conversion_script": "评论区留下预算和用途，私信发实物图，我先帮你判断该重点看哪里。",
        "risk_notes": ["不要承诺保真升值", "不要使用绝对化价格话术"],
    }
```

- [ ] **Step 6: Run focused test and confirm the planned failure changes**

Run from `backend`:

```bash
python -m unittest tests.test_hot_copy_api
```

Expected: tests still fail on missing API/service routes, not on schema import or mock output.

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/hot_copy.py backend/app/prompts/hot_copy_prompt.py backend/app/llm/llm_gateway.py backend/tests/test_hot_copy_api.py
git commit -m "feat: add hot copy prompt contracts"
```

---

### Task 3: Backend Service

**Files:**
- Create: `backend/app/services/hot_copy_service.py`
- Test: `backend/tests/test_hot_copy_api.py`

- [ ] **Step 1: Extend backend tests for service behavior through API**

Append these tests to `HotCopyApiTest`:

```python
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
```

- [ ] **Step 2: Run tests and confirm failure**

Run from `backend`:

```bash
python -m unittest tests.test_hot_copy_api
```

Expected: route/service failure because endpoints are not implemented.

- [ ] **Step 3: Create service implementation**

Create `backend/app/services/hot_copy_service.py`:

```python
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.llm.llm_gateway import LLMGateway, LLMGatewayRequest, LLMGatewayResponse
from app.models.hot_copy import HotCopyMaterial, HotCopyRewrite
from app.models.project import Project
from app.prompts.hot_copy_prompt import (
    HOT_COPY_ANALYSIS_MODULE,
    HOT_COPY_ANALYSIS_OUTPUT_SCHEMA,
    HOT_COPY_ANALYSIS_PROMPT_VERSION,
    HOT_COPY_REWRITE_MODULE,
    HOT_COPY_REWRITE_OUTPUT_SCHEMA,
    HOT_COPY_REWRITE_PROMPT_VERSION,
    build_hot_copy_analysis_prompts,
    build_hot_copy_rewrite_prompts,
)
from app.schemas.hot_copy import HotCopyMaterialManualCreate, HotCopyRewriteRequest
from app.services import credit_service, project_service


REDIANBAO_NOT_CONNECTED_MESSAGE = "热点宝数据源暂未接入，请先使用手动输入。"


def list_materials(db: Session, user_id: int, skip: int = 0, limit: int = 50) -> list[HotCopyMaterial]:
    statement = (
        select(HotCopyMaterial)
        .where(HotCopyMaterial.user_id == user_id)
        .order_by(HotCopyMaterial.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def get_material_for_user(db: Session, material_id: int, user_id: int) -> HotCopyMaterial | None:
    material = db.get(HotCopyMaterial, material_id)
    if material is None or material.user_id != user_id:
        return None
    return material


def create_manual_material(db: Session, payload: HotCopyMaterialManualCreate, user_id: int) -> HotCopyMaterial:
    project_id = validate_project_id(db, payload.project_id, user_id)
    material = HotCopyMaterial(
        user_id=user_id,
        project_id=project_id,
        platform=payload.platform,
        source_type="manual",
        source_url=payload.source_url,
        account_name=payload.account_name,
        account_home_url=payload.account_home_url,
        cover_url=payload.cover_url,
        title=payload.title,
        original_script=payload.original_script,
        metrics_json=payload.metrics_json,
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


def analyze_material(db: Session, material_id: int, user_id: int) -> tuple[HotCopyMaterial, dict[str, Any], int | None]:
    material = require_material(db, material_id, user_id)
    credit_service.ensure_sufficient_credits(db, user_id, credit_service.TEXT_GENERATION_COST)
    system_prompt, user_prompt = build_hot_copy_analysis_prompts(material)
    result = LLMGateway().generate(
        db=db,
        project_id=material.project_id,
        user_id=user_id,
        prompt_version=HOT_COPY_ANALYSIS_PROMPT_VERSION,
        request=LLMGatewayRequest(
            module_name=HOT_COPY_ANALYSIS_MODULE,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=HOT_COPY_ANALYSIS_OUTPUT_SCHEMA,
            temperature=0.4,
            max_tokens=2500,
            metadata={"material_id": material.id, "title": material.title, "platform": material.platform},
        ),
    )
    if not result.success:
        raise gateway_error(result)
    analysis = ensure_dict(result.data)
    material.analysis_json = analysis
    credit_service.charge_credits(
        db,
        user_id=user_id,
        cost=credit_service.TEXT_GENERATION_COST,
        reason="hot_copy_analysis",
        reference_type="generation_record",
        reference_id=result.generation_record_id,
        commit=False,
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return material, analysis, result.generation_record_id


def rewrite_material(
    db: Session,
    material_id: int,
    payload: HotCopyRewriteRequest,
    user_id: int,
) -> tuple[HotCopyRewrite, dict[str, Any], int | None]:
    material = require_material(db, material_id, user_id)
    project = get_optional_project(db, payload.project_id or material.project_id, user_id)
    project_id = project.id if project else None
    credit_service.ensure_sufficient_credits(db, user_id, credit_service.TEXT_GENERATION_COST)
    system_prompt, user_prompt = build_hot_copy_rewrite_prompts(material, project, payload)
    result = LLMGateway().generate(
        db=db,
        project_id=project_id,
        user_id=user_id,
        prompt_version=HOT_COPY_REWRITE_PROMPT_VERSION,
        request=LLMGatewayRequest(
            module_name=HOT_COPY_REWRITE_MODULE,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=HOT_COPY_REWRITE_OUTPUT_SCHEMA,
            temperature=0.7,
            max_tokens=3500,
            metadata={
                "material_id": material.id,
                "project_id": project_id,
                "rewrite_mode": payload.rewrite_mode,
                "duration": payload.duration,
                "conversion_goal": payload.conversion_goal,
                "product": payload.product or (project.product if project else None),
            },
        ),
    )
    if not result.success:
        raise gateway_error(result)
    output = ensure_dict(result.data)
    rewrite = HotCopyRewrite(
        material_id=material.id,
        user_id=user_id,
        project_id=project_id,
        rewrite_mode=payload.rewrite_mode,
        duration=payload.duration,
        conversion_goal=payload.conversion_goal,
        input_json=payload.model_dump(mode="json"),
        output_json=output,
        generation_record_id=result.generation_record_id,
    )
    db.add(rewrite)
    credit_service.charge_credits(
        db,
        user_id=user_id,
        cost=credit_service.TEXT_GENERATION_COST,
        reason="hot_copy_rewrite",
        reference_type="generation_record",
        reference_id=result.generation_record_id,
        commit=False,
    )
    db.commit()
    db.refresh(rewrite)
    return rewrite, output, result.generation_record_id


def redianbao_reserved_response() -> dict[str, Any]:
    return {"connected": False, "message": REDIANBAO_NOT_CONNECTED_MESSAGE, "items": []}


def validate_project_id(db: Session, project_id: int | None, user_id: int) -> int | None:
    if project_id is None:
        return None
    project = project_service.get_project_for_user(db, project_id, user_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    return project.id


def get_optional_project(db: Session, project_id: int | None, user_id: int) -> Project | None:
    if project_id is None:
        return None
    project = project_service.get_project_for_user(db, project_id, user_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    return project


def require_material(db: Session, material_id: int, user_id: int) -> HotCopyMaterial:
    material = get_material_for_user(db, material_id, user_id)
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="爆款素材不存在")
    return material


def gateway_error(result: LLMGatewayResponse) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=result.error or "爆款文案生成失败",
    )


def ensure_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
```

- [ ] **Step 4: Run tests and confirm service import succeeds**

Run from `backend`:

```bash
python -m unittest tests.test_hot_copy_api
```

Expected: route failure remains until Task 4.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/hot_copy_service.py backend/tests/test_hot_copy_api.py
git commit -m "feat: add hot copy service"
```

---

### Task 4: Backend API Routes

**Files:**
- Create: `backend/app/api/hot_copy.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_hot_copy_api.py`

- [ ] **Step 1: Add ownership and Redianbao tests**

Append these tests to `HotCopyApiTest`:

```python
def test_user_cannot_read_other_users_material(self) -> None:
    material = self.create_material()
    self.register_user("other", "other@example.com")

    detail = self.client.get(f"/api/hot-copy/materials/{material['id']}")
    analyze = self.client.post(f"/api/hot-copy/materials/{material['id']}/analyze")

    self.assertEqual(detail.status_code, 404)
    self.assertEqual(analyze.status_code, 404)

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
```

- [ ] **Step 2: Create API routes**

Create `backend/app/api/hot_copy.py`:

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.hot_copy import (
    HotCopyAnalysisResponse,
    HotCopyMaterialManualCreate,
    HotCopyMaterialRead,
    HotCopyRedianbaoSearchRequest,
    HotCopyRewriteRequest,
    HotCopyRewriteResponse,
)
from app.services import hot_copy_service


router = APIRouter(tags=["hot_copy"])


def success_response(data: object, message: str = "") -> dict[str, object]:
    return {"success": True, "data": data, "message": message}


def failure_response(data: object, message: str) -> dict[str, object]:
    return {"success": False, "data": data, "message": message}


@router.post("/api/hot-copy/materials/manual", status_code=201)
def create_manual_material_api(
    payload: HotCopyMaterialManualCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    material = hot_copy_service.create_manual_material(db, payload, current_user.id)
    return success_response(HotCopyMaterialRead.model_validate(material).model_dump(mode="json"), "爆款素材已保存")


@router.get("/api/hot-copy/materials")
def list_materials_api(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    materials = hot_copy_service.list_materials(db, current_user.id, skip=skip, limit=limit)
    return success_response([HotCopyMaterialRead.model_validate(item).model_dump(mode="json") for item in materials])


@router.get("/api/hot-copy/materials/{material_id}")
def get_material_api(
    material_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    material = hot_copy_service.require_material(db, material_id, current_user.id)
    return success_response(HotCopyMaterialRead.model_validate(material).model_dump(mode="json"))


@router.post("/api/hot-copy/materials/{material_id}/analyze")
def analyze_material_api(
    material_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    material, analysis, generation_record_id = hot_copy_service.analyze_material(db, material_id, current_user.id)
    response = HotCopyAnalysisResponse(
        material=HotCopyMaterialRead.model_validate(material),
        analysis=analysis,
        generation_record_id=generation_record_id,
    )
    return success_response(response.model_dump(mode="json"), "爆点拆解完成")


@router.post("/api/hot-copy/materials/{material_id}/rewrite")
def rewrite_material_api(
    material_id: int,
    payload: HotCopyRewriteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    rewrite, output, generation_record_id = hot_copy_service.rewrite_material(db, material_id, payload, current_user.id)
    response = HotCopyRewriteResponse(
        rewrite=rewrite,
        output=output,
        generation_record_id=generation_record_id,
    )
    return success_response(response.model_dump(mode="json"), "文案仿写完成")


@router.post("/api/hot-copy/redianbao/search")
def search_redianbao_api(
    payload: HotCopyRedianbaoSearchRequest,
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    del payload, current_user
    data = hot_copy_service.redianbao_reserved_response()
    return failure_response(data, hot_copy_service.REDIANBAO_NOT_CONNECTED_MESSAGE)
```

Modify `backend/app/main.py` to import and include the router:

```python
from app.api import hot_copy
```

```python
app.include_router(hot_copy.router)
```

- [ ] **Step 3: Run backend tests**

Run from `backend`:

```bash
python -m unittest tests.test_hot_copy_api tests.test_generation_records_api tests.test_alembic_migrations
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/hot_copy.py backend/app/main.py backend/tests/test_hot_copy_api.py
git commit -m "feat: add hot copy api"
```

---

### Task 5: Frontend API, Navigation, And History

**Files:**
- Create: `frontend-v2/src/lib/api/hotCopy.ts`
- Modify: `frontend-v2/src/lib/api/generationRecords.ts`
- Modify: `frontend-v2/src/app/history/HistoryClient.tsx`
- Modify: `frontend-v2/src/components/AppShell.tsx`
- Create: `frontend-v2/tests/hotCopyEntry.test.ts`
- Create: `frontend-v2/tests/hotCopyHistory.test.ts`

- [ ] **Step 1: Write frontend source tests**

Create `frontend-v2/tests/hotCopyEntry.test.ts`:

```typescript
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import test from "node:test";

test("hot copy workspace is wired into navigation and api helpers", () => {
  const shell = readFileSync("src/components/AppShell.tsx", "utf8");

  assert.match(shell, /爆款仿写/);
  assert.match(shell, /\/hot-copy/);
  assert.ok(existsSync("src/lib/api/hotCopy.ts"));
  const api = readFileSync("src/lib/api/hotCopy.ts", "utf8");
  for (const path of [
    "/api/hot-copy/materials/manual",
    "/api/hot-copy/materials",
    "/api/hot-copy/materials/${materialId}/analyze",
    "/api/hot-copy/materials/${materialId}/rewrite",
    "/api/hot-copy/redianbao/search",
  ]) {
    assert.match(api, new RegExp(path.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }
});
```

Create `frontend-v2/tests/hotCopyHistory.test.ts`:

```typescript
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

test("generation history exposes hot copy modules", () => {
  const apiSource = readFileSync("src/lib/api/generationRecords.ts", "utf8");
  const historySource = readFileSync("src/app/history/HistoryClient.tsx", "utf8");

  for (const moduleName of ["hot_copy_analysis", "hot_copy_rewrite"]) {
    assert.match(apiSource, new RegExp(`"${moduleName}"`));
    assert.match(historySource, new RegExp(`value: "${moduleName}"`));
  }

  assert.match(apiSource, /爆点拆解/);
  assert.match(apiSource, /爆款仿写/);
});
```

- [ ] **Step 2: Run tests and confirm failure**

Run from `frontend-v2`:

```bash
node --experimental-strip-types --test tests\hotCopyEntry.test.ts tests\hotCopyHistory.test.ts
```

Expected: tests fail because API helper, route, and labels do not exist.

- [ ] **Step 3: Create typed frontend API helper**

Create `frontend-v2/src/lib/api/hotCopy.ts`:

```typescript
import { api } from "./client";

export interface HotCopyMaterial {
  id: number;
  user_id: number;
  project_id: number | null;
  platform: string;
  source_type: string;
  source_url: string | null;
  account_name: string | null;
  account_home_url: string | null;
  cover_url: string | null;
  title: string;
  original_script: string;
  metrics_json: Record<string, unknown>;
  analysis_json: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface CreateManualHotCopyPayload {
  project_id?: number | null;
  platform: "douyin";
  source_url?: string | null;
  account_name?: string | null;
  account_home_url?: string | null;
  cover_url?: string | null;
  title: string;
  original_script: string;
  metrics_json?: Record<string, unknown>;
}

export interface HotCopyAnalysisResponse {
  material: HotCopyMaterial;
  analysis: Record<string, unknown>;
  generation_record_id: number | null;
}

export interface HotCopyRewritePayload {
  project_id?: number | null;
  rewrite_mode: "light" | "medium" | "strong";
  duration: "30s" | "60s" | "90s";
  conversion_goal: string;
  product?: string | null;
  target_customer?: string | null;
  account_persona?: string | null;
}

export interface HotCopyRewriteResponse {
  rewrite: {
    id: number;
    material_id: number;
    user_id: number;
    project_id: number | null;
    rewrite_mode: string;
    duration: string;
    conversion_goal: string;
    input_json: Record<string, unknown>;
    output_json: Record<string, unknown>;
    generation_record_id: number | null;
    created_at: string;
  };
  output: Record<string, unknown>;
  generation_record_id: number | null;
}

export async function createManualHotCopyMaterial(payload: CreateManualHotCopyPayload): Promise<HotCopyMaterial> {
  return api.post<HotCopyMaterial>("/api/hot-copy/materials/manual", payload, { timeoutMs: 20000 });
}

export async function listHotCopyMaterials(): Promise<HotCopyMaterial[]> {
  return api.get<HotCopyMaterial[]>("/api/hot-copy/materials");
}

export async function analyzeHotCopyMaterial(materialId: number): Promise<HotCopyAnalysisResponse> {
  return api.post<HotCopyAnalysisResponse>(`/api/hot-copy/materials/${materialId}/analyze`, {}, { timeoutMs: 90000 });
}

export async function rewriteHotCopyMaterial(
  materialId: number,
  payload: HotCopyRewritePayload,
): Promise<HotCopyRewriteResponse> {
  return api.post<HotCopyRewriteResponse>(`/api/hot-copy/materials/${materialId}/rewrite`, payload, { timeoutMs: 90000 });
}

export async function searchRedianbaoHotCopy(keyword: string, count = 30): Promise<unknown> {
  return api.post<unknown>("/api/hot-copy/redianbao/search", { keyword, platform: "douyin", count }, { timeoutMs: 20000 });
}
```

- [ ] **Step 4: Add navigation and history labels**

Modify `frontend-v2/src/components/AppShell.tsx`:

```typescript
{ label: "爆款仿写", mobileLabel: "仿写", to: "/hot-copy" },
```

Place it after `AI爆款拆解`.

Modify `frontend-v2/src/lib/api/generationRecords.ts`:

```typescript
  | "hot_copy_analysis"
  | "hot_copy_rewrite"
```

```typescript
  hot_copy_analysis: "爆点拆解",
  hot_copy_rewrite: "爆款仿写",
```

Modify `frontend-v2/src/app/history/HistoryClient.tsx` `moduleOptions`:

```typescript
  { label: "爆点拆解", value: "hot_copy_analysis" },
  { label: "爆款仿写", value: "hot_copy_rewrite" },
```

Modify `moduleTagClass`:

```typescript
if (module === "hot_copy_analysis" || module === "hot_copy_rewrite") return "bg-[rgba(245,158,11,0.15)] text-[#f59e0b]";
```

- [ ] **Step 5: Run frontend tests**

Run from `frontend-v2`:

```bash
node --experimental-strip-types --test tests\hotCopyEntry.test.ts tests\hotCopyHistory.test.ts tests\historyMediaRecords.test.ts
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add frontend-v2/src/lib/api/hotCopy.ts frontend-v2/src/lib/api/generationRecords.ts frontend-v2/src/app/history/HistoryClient.tsx frontend-v2/src/components/AppShell.tsx frontend-v2/tests/hotCopyEntry.test.ts frontend-v2/tests/hotCopyHistory.test.ts
git commit -m "feat: wire hot copy frontend entry"
```

---

### Task 6: Hot Copy Workbench Page

**Files:**
- Create: `frontend-v2/src/app/hot-copy/page.tsx`
- Modify: `frontend-v2/src/app/globals.css`
- Create: `frontend-v2/tests/hotCopyPage.test.ts`

- [ ] **Step 1: Write page source test**

Create `frontend-v2/tests/hotCopyPage.test.ts`:

```typescript
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import test from "node:test";

test("hot copy page contains manual douyin workflow and reserved redianbao entry", () => {
  assert.ok(existsSync("src/app/hot-copy/page.tsx"));
  const source = readFileSync("src/app/hot-copy/page.tsx", "utf8");

  for (const text of ["手动输入", "抖音", "热点宝", "保存素材", "拆解爆点", "仿写文案", "去生成视频"]) {
    assert.match(source, new RegExp(text));
  }

  for (const fn of [
    "createManualHotCopyMaterial",
    "listHotCopyMaterials",
    "analyzeHotCopyMaterial",
    "rewriteHotCopyMaterial",
    "searchRedianbaoHotCopy",
  ]) {
    assert.match(source, new RegExp(fn));
  }

  assert.doesNotMatch(source, /window\.location/);
});
```

- [ ] **Step 2: Run test and confirm failure**

Run from `frontend-v2`:

```bash
node --experimental-strip-types --test tests\hotCopyPage.test.ts
```

Expected: fail because `/hot-copy` page does not exist.

- [ ] **Step 3: Create the page**

Create `frontend-v2/src/app/hot-copy/page.tsx` as a client component. Use the existing `page-section`, `section-header`, `topic-workspace-plate`, `topic-control-panel`, `metal-input`, `metal-btn`, `metal-btn-primary`, `metal-tag`, and `topic-empty-state` classes. The page state and handlers must include these exact imports and functions:

```typescript
"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  analyzeHotCopyMaterial,
  createManualHotCopyMaterial,
  listHotCopyMaterials,
  rewriteHotCopyMaterial,
  searchRedianbaoHotCopy,
  type HotCopyMaterial,
} from "@/lib/api/hotCopy";
```

Implement these state fields:

```typescript
const [materials, setMaterials] = useState<HotCopyMaterial[]>([]);
const [selectedMaterial, setSelectedMaterial] = useState<HotCopyMaterial | null>(null);
const [title, setTitle] = useState("");
const [originalScript, setOriginalScript] = useState("");
const [sourceUrl, setSourceUrl] = useState("");
const [accountName, setAccountName] = useState("");
const [accountHomeUrl, setAccountHomeUrl] = useState("");
const [coverUrl, setCoverUrl] = useState("");
const [projectId, setProjectId] = useState("");
const [rewriteMode, setRewriteMode] = useState<"light" | "medium" | "strong">("medium");
const [duration, setDuration] = useState<"30s" | "60s" | "90s">("60s");
const [conversionGoal, setConversionGoal] = useState("私信获客");
const [product, setProduct] = useState("");
const [targetCustomer, setTargetCustomer] = useState("");
const [accountPersona, setAccountPersona] = useState("");
const [analysis, setAnalysis] = useState<Record<string, unknown> | null>(null);
const [rewriteOutput, setRewriteOutput] = useState<Record<string, unknown> | null>(null);
const [loading, setLoading] = useState<"" | "save" | "analyze" | "rewrite" | "redianbao">("");
const [error, setError] = useState("");
const [notice, setNotice] = useState("");
```

Implement `refreshMaterials`, `saveMaterial`, `analyzeSelected`, `rewriteSelected`, `openRedianbaoReserved`, and `selectMaterial` with button-local loading only. Do not add a full-page loading overlay. The required handler behavior is:

```typescript
async function openRedianbaoReserved() {
  setLoading("redianbao");
  setError("");
  setNotice("");
  try {
    await searchRedianbaoHotCopy("抖音口播爆款", 30);
  } catch (err) {
    setNotice(err instanceof Error ? err.message : "热点宝数据源暂未接入，请先使用手动输入。");
  } finally {
    setLoading("");
  }
}
```

Render three side-by-side panels on desktop and one-column on mobile:

```tsx
<div className="grid grid-cols-1 gap-5 xl:grid-cols-[1fr_1fr_1fr]">
  <div className="topic-control-panel">爆款素材 form and saved material list</div>
  <div className="topic-control-panel">爆点拆解 cards and analyze button</div>
  <div className="topic-control-panel">仿写文案 controls, output, and video link</div>
</div>
```

The video link must use the generated script:

```typescript
const rewriteScript = getString(rewriteOutput?.script);
const videoHref = rewriteScript ? `/videos?prompt=${encodeURIComponent(rewriteScript)}` : "/videos";
```

```tsx
<Link className="metal-btn metal-btn-primary inline-flex" href={videoHref}>
  去生成视频
</Link>
```

Render the reserved Redianbao button near the top:

```tsx
<button className="metal-btn" type="button" onClick={openRedianbaoReserved} disabled={loading === "redianbao"}>
  热点宝每日热门搜索
</button>
```

- [ ] **Step 4: Add exact CSS**

Append to `frontend-v2/src/app/globals.css`:

```css
.hot-copy-page textarea.metal-input {
  min-height: 180px;
  resize: vertical;
}

.hot-copy-page select.metal-input {
  appearance: auto;
}
```

- [ ] **Step 5: Run frontend tests**

Run from `frontend-v2`:

```bash
node --experimental-strip-types --test tests\hotCopyEntry.test.ts tests\hotCopyHistory.test.ts tests\hotCopyPage.test.ts tests\historyMediaRecords.test.ts
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add frontend-v2/src/app/hot-copy/page.tsx frontend-v2/src/app/globals.css frontend-v2/tests/hotCopyPage.test.ts
git commit -m "feat: add hot copy workbench"
```

---

### Task 7: Verification, Browser QA, Push, And Deploy

**Files:**
- Feature files from previous tasks only.

- [ ] **Step 1: Run backend focused tests**

Run from `backend`:

```bash
python -m unittest tests.test_hot_copy_api tests.test_generation_records_api tests.test_alembic_migrations
```

Expected: all pass.

- [ ] **Step 2: Run frontend source tests**

Run from `frontend-v2`:

```bash
node --experimental-strip-types --test tests\*.test.ts
```

Expected: all pass.

- [ ] **Step 3: Run lint and build**

Run from `frontend-v2`:

```bash
npm run lint
npm run build
```

Expected: lint exits 0; build exits 0.

- [ ] **Step 4: Run gstack browser QA**

Start the app using the existing local dev setup. Use gstack:

```bash
$B goto http://localhost:5173/hot-copy
$B snapshot -i
$B fill @<title-input> "买翡翠别先问最低价"
$B fill @<script-textarea> "新手买翡翠，别一上来就问最低价。先看种水，再看纹裂，再看证书。"
$B click @<save-button>
$B snapshot -D
$B click @<analyze-button>
$B snapshot -D
$B click @<rewrite-button>
$B snapshot -D
$B click @<redianbao-button>
$B snapshot -D
$B console --errors
```

Expected:

- `/hot-copy` opens.
- Navigation remains clickable during initial data load.
- Manual material saves.
- Analysis result appears.
- Rewrite result appears.
- Redianbao reserved message appears.
- Console has no runtime errors.

Use real element refs from `$B snapshot -i`.

- [ ] **Step 5: Commit QA fixes after test-first changes**

When QA exposes a bug, write or update a focused test first, then commit:

```bash
git add <changed-files>
git commit -m "fix: stabilize hot copy workflow"
```

- [ ] **Step 6: Push**

Push the branch:

```bash
git push origin main
```

Push to the user-confirmed GitHub repository with the local SSH key:

```bash
git -c core.sshCommand="ssh -i C:/Users/chuyu/.ssh/id_ed25519_chuyu112_jsvoc -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new" push git@github.com:chuyu112/JSVOC.git main:main
```

- [ ] **Step 7: Deploy**

Create a release archive:

```powershell
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$sha = (git rev-parse --short HEAD).Trim()
New-Item -ItemType Directory -Path .deploy -Force | Out-Null
$path = ".deploy/JSVOC_git_${sha}_${stamp}.tar.gz"
git archive --format=tar.gz -o $path HEAD
Write-Output $path
```

Upload using the existing Paramiko deploy flow, then run on the server:

```bash
docker compose -p jsvoc --progress plain up -d --build
docker compose -p jsvoc ps
curl -sS -o /tmp/jsvoc_backend_health.txt -w "%{http_code}" http://localhost:8000/health
curl -sS -o /tmp/jsvoc_frontend_hot_copy.txt -w "%{http_code}" http://localhost:5173/hot-copy
```

Expected:

- backend health returns `200`
- `/hot-copy` returns `200`
- backend container is healthy
- frontend container is running
- postgres container is healthy

---

## Scope Guardrails

- First version is Douyin only.
- First version accepts manual entry only.
- Redianbao has a visible UI/API entry and returns a not-connected message.
- No automatic Douyin crawling.
- No new video generation backend path; the workbench links to the existing video page with the rewritten script.
- No credit charge for saving manual material.
- Charge `TEXT_GENERATION_COST` only after successful analysis or successful rewrite.
- Every analysis and rewrite attempt creates a `generation_records` row through `LLMGateway`.

## Self-Review Checklist

- Manual input maps to Task 4 API and Task 6 UI.
- Douyin first version maps to `platform: "douyin"` and Chinese UI labels.
- Redianbao reserved entry maps to Task 4 API and Task 6 UI.
- AI calls go through `LLMGateway` in Task 3.
- Generation history maps to `hot_copy_analysis` and `hot_copy_rewrite` in Task 5.
- Migration chain uses `down_revision = "20260524_0012"`.
- Loading UX is button-local and verified in Task 7.
- No secrets are added.
