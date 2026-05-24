import asyncio
import unittest
from unittest.mock import patch

from app.main import lifespan


class _DummySession:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class AppLifespanTest(unittest.TestCase):
    def test_recovers_provider_tasks_before_failing_stale_local_tasks(self) -> None:
        events: list[str] = []

        async def run_lifespan() -> None:
            with (
                patch("app.main.SessionLocal", return_value=_DummySession()),
                patch(
                    "app.main.recover_interrupted_video_generation_tasks",
                    side_effect=lambda: events.append("recover"),
                ),
                patch(
                    "app.main.fail_stale_generation_tasks",
                    side_effect=lambda _db: events.append("fail_stale"),
                ),
                patch("app.main.close_http_client"),
            ):
                async with lifespan(object()):
                    events.append("yield")

        asyncio.run(run_lifespan())

        self.assertEqual(events, ["recover", "fail_stale", "yield"])
