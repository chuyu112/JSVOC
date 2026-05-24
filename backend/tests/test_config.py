import unittest

from app.core.config import Settings
from app.services.video_generation_service import video_api_key


class ConfigTest(unittest.TestCase):
    def test_default_llm_timeout_allows_long_generation_tasks(self) -> None:
        settings = Settings(_env_file=None)

        self.assertEqual(settings.llm_timeout_seconds, 180.0)

    def test_default_video_generation_model_is_seedance_standard(self) -> None:
        settings = Settings(_env_file=None)

        self.assertEqual(settings.video_generation_model, "seedance-2.0")

    def test_default_hot_video_search_provider_is_auto(self) -> None:
        settings = Settings(_env_file=None)

        self.assertEqual(settings.hot_video_search_provider, "auto")
        self.assertEqual(settings.opencli_hot_video_search_command, "")

    def test_ark_api_key_is_video_generation_fallback(self) -> None:
        settings = Settings(
            _env_file=None,
            VIDEO_GENERATION_API_KEY="",
            ARK_API_KEY="ark-test-key",
        )

        self.assertEqual(video_api_key(settings), "ark-test-key")


if __name__ == "__main__":
    unittest.main()
