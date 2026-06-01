import base64
import unittest
from io import BytesIO

from PIL import Image

from app.schemas.image_generation import ImageEditRequest, ImageReferenceInput
from app.services import image_generation_service


class ImageReferenceCompressionTest(unittest.TestCase):
    def test_build_image_edit_prompt_preserves_global_image_mentions(self) -> None:
        payload = ImageEditRequest(
            prompt="@图片1 和 @图片2 一起去 @图片3 吃饭",
            reference_images=[
                ImageReferenceInput(
                    reference_image_type="persona",
                    reference_image_name="@图片1",
                    source_image_base64="YWJj",
                    source_image_mime="image/png",
                    source_image_filename="person-a.png",
                ),
                ImageReferenceInput(
                    reference_image_type="persona",
                    reference_image_name="@图片2",
                    source_image_base64="YWJj",
                    source_image_mime="image/png",
                    source_image_filename="person-b.png",
                ),
                ImageReferenceInput(
                    reference_image_type="location",
                    reference_image_name="@图片3",
                    source_image_base64="YWJj",
                    source_image_mime="image/png",
                    source_image_filename="restaurant.png",
                ),
            ],
        )

        prompt = image_generation_service.build_image_edit_prompt(payload)

        self.assertIn("@图片1：人设参考图，文件名 person-a.png。", prompt)
        self.assertIn("@图片2：人设参考图，文件名 person-b.png。", prompt)
        self.assertIn("@图片3：场景参考图，文件名 restaurant.png。", prompt)
        self.assertIn("严格按下面的参考图名称绑定到对应文件", prompt)

    def test_prepare_edit_image_files_compresses_large_reference_before_provider_request(self) -> None:
        image = Image.effect_noise((1800, 1800), 100).convert("RGB")
        source = BytesIO()
        image.save(source, format="PNG")
        source_bytes = source.getvalue()
        self.assertGreater(len(source_bytes), image_generation_service.MAX_PROVIDER_MULTIPART_IMAGE_BYTES)

        files = image_generation_service.prepare_edit_image_files(
            [
                ImageReferenceInput(
                    reference_image_type="persona",
                    source_image_base64=base64.b64encode(source_bytes).decode("ascii"),
                    source_image_mime="image/png",
                    source_image_filename="large-reference.png",
                )
            ]
        )

        self.assertEqual(len(files), 1)
        field_name, file_tuple = files[0]
        filename, prepared_bytes, prepared_mime = file_tuple

        self.assertEqual(field_name, "image")
        self.assertEqual(filename, "large-reference.jpg")
        self.assertEqual(prepared_mime, "image/jpeg")
        self.assertLessEqual(
            len(prepared_bytes),
            image_generation_service.MAX_PROVIDER_MULTIPART_IMAGE_BYTES,
        )


if __name__ == "__main__":
    unittest.main()
