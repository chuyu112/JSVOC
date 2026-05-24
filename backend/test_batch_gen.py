import sys
sys.stdout.reconfigure(encoding='utf-8')

from app.db.session import SessionLocal
from app.schemas.topic import TopicBatchGenerateRequest
from app.services import topic_service

db = SessionLocal()

payload = TopicBatchGenerateRequest(
    project_id=2,
    platform="抖音",
    goal="获客",
    content_format="video",
    target_count=15,
    temperature=0.7,
)

print("Starting batch generation: 15 topics (3x5 concurrent)...")
result = topic_service.generate_topics_batch(db, payload, user_id=4)

print(f"\nTarget: {result['target_count']}")
print(f"Generated: {result['generated_count']}")
print(f"Latency: {result['latency_ms']}ms")
print(f"Provider: {result['provider']}")
print(f"Model: {result['model']}")

for idx, topic in enumerate(result['topics'], 1):
    print(f"\n【{idx}】{topic.title}")
