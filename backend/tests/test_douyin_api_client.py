import os
import unittest
from unittest.mock import Mock, patch

from app.services.douyin_api_client import DouyinAPIClient


class _FakeStreamResponse:
    def __init__(self, *, headers: dict[str, str], chunks: list[bytes]) -> None:
        self.headers = headers
        self._chunks = chunks

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self) -> None:
        return None

    def iter_bytes(self):
        yield from self._chunks


class DouyinApiClientTest(unittest.TestCase):
    def test_download_video_rejects_oversized_content_length_before_writing_file(self) -> None:
        client = DouyinAPIClient(base_url="http://127.0.0.1")
        client.client = Mock()
        client.client.stream.return_value = _FakeStreamResponse(
            headers={"content-length": str(300 * 1024 * 1024)},
            chunks=[b"x"],
        )

        with patch("os.remove") as remove_file:
            with self.assertRaisesRegex(RuntimeError, "too large"):
                client.download_video("https://www.douyin.com/video/123")

        remove_file.assert_called_once()

    def test_download_video_rejects_stream_that_exceeds_size_limit(self) -> None:
        client = DouyinAPIClient(base_url="http://127.0.0.1")
        client.client = Mock()
        client.client.stream.return_value = _FakeStreamResponse(
            headers={},
            chunks=[b"x" * (64 * 1024), b"y" * (64 * 1024)],
        )

        with patch("app.services.douyin_api_client.MAX_DOUYIN_DOWNLOAD_BYTES", 80 * 1024, create=True):
            with self.assertRaisesRegex(RuntimeError, "too large"):
                path = client.download_video("https://www.douyin.com/video/123")
                if os.path.exists(path):
                    os.remove(path)


if __name__ == "__main__":
    unittest.main()
