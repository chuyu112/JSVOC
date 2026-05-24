from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.ai_chat import router as ai_chat_router
from app.api.auth import router as auth_router
from app.api.credits import router as credits_router
from app.api.digital_assets import router as digital_assets_router
from app.api.generation_records import router as generation_records_router
from app.api.generation_tasks import router as generation_tasks_router
from app.api.hot_videos import router as hot_videos_router
from app.api.image_generation import router as image_generation_router
from app.api.llm_test import router as llm_test_router
from app.api.projects import router as projects_router
from app.api.reference_images import router as reference_images_router
from app.api.scripts import router as scripts_router
from app.api.strategy_bundle import router as strategy_bundle_router
from app.api.topics import router as topics_router
from app.api.video_generation import router as video_generation_router
from app.api.video_generation import recover_interrupted_video_generation_tasks
from app.core.config import get_settings
from app.db.base import init_db
from app.db.session import SessionLocal
from app.llm.llm_gateway import close_http_client
from app.services.generation_task_service import fail_stale_generation_tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    recover_interrupted_video_generation_tasks()
    with SessionLocal() as db:
        fail_stale_generation_tasks(db)
    try:
        yield
    finally:
        close_http_client()


settings = get_settings()

app = FastAPI(title="AI Short Video Ops API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(ai_chat_router)
app.include_router(credits_router)
app.include_router(projects_router)
app.include_router(llm_test_router)
app.include_router(strategy_bundle_router)
app.include_router(topics_router)
app.include_router(scripts_router)
app.include_router(digital_assets_router)
app.include_router(image_generation_router)
app.include_router(reference_images_router)
app.include_router(video_generation_router)
app.include_router(generation_records_router)
app.include_router(generation_tasks_router)
app.include_router(hot_videos_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"message": "AI Short Video Ops API is running"}
