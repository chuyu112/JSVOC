import unittest

from app.services.opencli_search_service import render_command_template


class OpenCliSearchServiceTest(unittest.TestCase):
    def test_render_command_template_rejects_raw_placeholders(self) -> None:
        with self.assertRaises(KeyError):
            render_command_template(
                "opencli search {keyword_raw}",
                {
                    "query": "safe query",
                    "keyword": "jade; rm -rf /",
                    "platform": "douyin",
                    "focus": "hot",
                    "count": "5",
                    "project": "jade",
                },
            )


if __name__ == "__main__":
    unittest.main()
