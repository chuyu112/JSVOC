from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.account_package import router as account_package_router
from app.api.execution_plan import router as execution_plan_router
from app.api.generation_records import router as generation_records_router
from app.api.gateway_providers import router as gateway_providers_router
from app.api.llm_test import router as llm_test_router
from app.api.projects import router as projects_router
from app.api.scripts import router as scripts_router
from app.api.topics import router as topics_router
from app.core.config import get_settings
from app.db.base import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


settings = get_settings()

app = FastAPI(title="AI Short Video Ops API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(projects_router)
app.include_router(llm_test_router)
app.include_router(account_package_router)
app.include_router(execution_plan_router)
app.include_router(topics_router)
app.include_router(scripts_router)
app.include_router(generation_records_router)
app.include_router(gateway_providers_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"message": "AI Short Video Ops API is running"}
