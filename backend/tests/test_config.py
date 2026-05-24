import unittest

from app.core.config import Settings


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


if __name__ == "__main__":
    unittest.main()
