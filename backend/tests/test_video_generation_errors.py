import unittest

import httpx

from app.api.video_generation import video_generation_error_message


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


if __name__ == '__main__':
    unittest.main()
