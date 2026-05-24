from typing import Any

from pydantic import BaseModel, Field


class ExecutionPlanGenerateRequest(BaseModel):
    project_id: int = Field(gt=0)
    cycle: str = Field(default="30天", min_length=1, max_length=40)
    daily_time: str = Field(default="2小时", min_length=1, max_length=40)
    temperature: float = Field(default=0.7, ge=0, le=2)


class WeeklyPlanItem(BaseModel):
    week: int = Field(ge=1)
    goal: str
    focus: str
    key_tasks: list[str] = Field(default_factory=list)


class DailyPlanItem(BaseModel):
    day: int = Field(ge=1)
    task: str
    topic: str
    shooting_task: str
    review_metrics: list[str]


class ExecutionPlanResult(BaseModel):
    cycle: str
    weekly_plan: list[WeeklyPlanItem]
    daily_plan: list[DailyPlanItem]
    notes: list[str] = Field(default_factory=list)


class ExecutionPlanGenerateResponse(BaseModel):
    execution_plan: ExecutionPlanResult
    generation_record_id: int | None
    provider: str
    model: str
    usage: dict[str, Any]
    latency_ms: int
