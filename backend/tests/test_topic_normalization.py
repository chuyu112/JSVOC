import unittest

from app.schemas.topic import TopicGenerateRequest
from app.services.topic_service import normalize_topics


class TopicNormalizationTest(unittest.TestCase):
    def test_normalize_topics_limits_copy_fields_to_under_200_chars(self) -> None:
        long_text = "翡翠" * 120
        payload = TopicGenerateRequest(project_id=1, platform="抖音", goal="获客", count=1)

        topics = normalize_topics(
            {
                "topics": [
                    {
                        "title": long_text,
                        "content_type": "避坑科普",
                        "platform": "抖音",
                        "goal": "获客",
                        "selling_point": long_text,
                        "user_pain_point": long_text,
                        "hook": long_text,
                        "shooting_suggestion": long_text,
                        "conversion_method": long_text,
                        "score": 90,
                    }
                ]
            },
            payload,
        )

        topic = topics[0]
        self.assertLess(len(topic.title), 200)
        self.assertLess(len(topic.selling_point or ""), 200)
        self.assertLess(len(topic.topic_data["user_pain_point"]), 200)
        self.assertLess(len(topic.topic_data["hook"]), 200)
        self.assertLess(len(topic.topic_data["shooting_suggestion"]), 200)
        self.assertLess(len(topic.topic_data["conversion_method"]), 200)

    def test_normalize_topics_keeps_media_generation_fields(self) -> None:
        payload = TopicGenerateRequest(
            project_id=1,
            platform="抖音",
            goal="获客",
            count=1,
            content_format="video",
        )

        topics = normalize_topics(
            {
                "topics": [
                    {
                        "title": "四会翡翠手镯自然光实拍",
                        "content_type": "实拍种草",
                        "platform": "抖音",
                        "goal": "获客",
                        "user_pain_point": "担心灯光下好看，实物不够真实",
                        "hook": "这只手镯别先看柜台灯，先看自然光。",
                        "shooting_suggestion": "真人拿手镯走到窗边，拍自然光、侧光和细节。",
                        "conversion_method": "评论预算和圈口，私信发自然光视频。",
                        "shooting_script": "开场展示柜台灯和自然光差别，再讲种水、棉和纹裂。",
                        "seedance_video_prompt": "参考图为翡翠手镯，生成自然光窗边实拍短视频。",
                        "image_prompt": "自然光窗边翡翠手镯产品图，清透真实，干净背景。",
                        "image_edit_prompt": "保留参考图手镯主体，改为自然光窗边场景，提升真实质感。",
                        "score": 92,
                    }
                ]
            },
            payload,
        )

        topic_data = topics[0].topic_data
        self.assertEqual(topic_data["content_format"], "video")
        self.assertEqual(topic_data["shooting_script"], "开场展示柜台灯和自然光差别，再讲种水、棉和纹裂。")
        self.assertEqual(topic_data["seedance_video_prompt"], "参考图为翡翠手镯，生成自然光窗边实拍短视频。")
        self.assertEqual(topic_data["image_prompt"], "自然光窗边翡翠手镯产品图，清透真实，干净背景。")
        self.assertEqual(topic_data["image_edit_prompt"], "保留参考图手镯主体，改为自然光窗边场景，提升真实质感。")


if __name__ == "__main__":
    unittest.main()
