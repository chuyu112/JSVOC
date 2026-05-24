import unittest
from unittest.mock import patch

import httpx

from app.api.video_generation import video_generation_error_message
from app.core.config import Settings
from app.services import video_generation_service


class VideoGenerationErrorMessageTest(unittest.TestCase):
    def test_privacy_reference_image_rejection_is_user_facing(self) -> None:
        request = httpx.Request('POST', 'https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks')
        response = httpx.Response(
            400,
            request=request,
            json={
                'error': {
                    'code': 'InputImageSensitiveContentDetected.PrivacyInformation',
                    'message': 'The request failed because the input image may contain real person.',
                }
            },
        )
        exc = httpx.HTTPStatusError('provider rejected request', request=request, response=response)

        message = video_generation_error_message(exc)

        self.assertIn('参考图未通过火山审核', message)
        self.assertIn('疑似包含真实人物或隐私信息', message)
        self.assertIn('积分已自动退回', message)

    def test_unknown_provider_error_keeps_raw_context(self) -> None:
        request = httpx.Request('POST', 'https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks')
        response = httpx.Response(404, request=request, json={'error': {'code': 'NotFound'}})
        exc = httpx.HTTPStatusError('provider rejected request', request=request, response=response)

        message = video_generation_error_message(exc)

        self.assertIn('video generation provider failed 404', message)

    def test_generate_video_requires_local_api_key_before_provider_call(self) -> None:
        settings = Settings(
            _env_file=None,
            VIDEO_GENERATION_BASE_URL='https://ark.cn-beijing.volces.com',
            VIDEO_GENERATION_API_KEY='',
            ARK_API_KEY='',
        )

        with (
            patch('app.services.video_generation_service.get_settings', return_value=settings),
            patch('app.services.video_generation_service.httpx.post') as post,
        ):
            with self.assertRaises(ValueError) as context:
                video_generation_service.generate_video('jade bracelet rotating')

        self.assertIn('VIDEO_GENERATION_API_KEY or ARK_API_KEY is required', str(context.exception))
        post.assert_not_called()


if __name__ == '__main__':
    unittest.main()
