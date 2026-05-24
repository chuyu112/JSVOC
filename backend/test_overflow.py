import sys
import time
sys.stdout.reconfigure(encoding='utf-8')

from app.db.session import SessionLocal
from app.schemas.topic import TopicBatchGenerateRequest
from app.services import topic_service

db = SessionLocal()

for target in [10, 20, 30]:
    payload = TopicBatchGenerateRequest(
        project_id=2,
        platform="抖音",
        goal="获客",
        content_format="video",
        target_count=target,
        temperature=0.7,
    )
    start = time.time()
    result = topic_service.generate_topics_batch(db, payload, user_id=4)
    elapsed = (time.time() - start) * 1000
    print(f"[{target:2d}] {elapsed:6.0f}ms | generated={result['generated_count']}/{result['target_count']}")
