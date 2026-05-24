import unittest

from app.services import storage_service


class StorageServiceTest(unittest.TestCase):
    def test_generated_image_without_project_uses_account_scope(self) -> None:
        object_key = storage_service.build_generated_image_object_key(
            user_id=7,
            project_id=None,
            mime_type="image/png",
        )

        self.assertTrue(object_key.startswith("users/7/account/images/"))
        self.assertTrue(object_key.endswith(".png"))

    def test_generated_video_without_project_uses_account_scope(self) -> None:
        object_key = storage_service.build_generated_video_object_key(
            user_id=7,
            project_id=None,
            mime_type="video/mp4",
        )

        self.assertTrue(object_key.startswith("users/7/account/videos/"))
        self.assertTrue(object_key.endswith(".mp4"))

    def test_reference_media_without_project_uses_account_scope(self) -> None:
        object_key = storage_service.build_reference_media_object_key(
            user_id=7,
            project_id=None,
            media_kind="images",
            mime_type="image/png",
        )

        self.assertTrue(object_key.startswith("users/7/account/references/images/"))
        self.assertTrue(object_key.endswith(".png"))


if __name__ == "__main__":
    unittest.main()
