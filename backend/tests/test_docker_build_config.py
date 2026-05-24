from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]


class DockerBuildConfigTest(unittest.TestCase):
    def test_backend_image_uses_configurable_pip_index_and_network_timeouts(self) -> None:
        dockerfile = (REPO_ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")
        compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

        self.assertIn("ARG PIP_INDEX_URL=", dockerfile)
        self.assertIn("PIP_DEFAULT_TIMEOUT", dockerfile)
        self.assertIn("PIP_RETRIES", dockerfile)
        self.assertIn("--timeout", dockerfile)
        self.assertIn("--retries", dockerfile)
        self.assertIn("PIP_INDEX_URL:", compose)


if __name__ == "__main__":
    unittest.main()
