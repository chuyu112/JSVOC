import unittest

from app.services.account_package_normalizer import normalize_account_package


class AccountPackageNormalizationTest(unittest.TestCase):
    def test_target_user_profile_accepts_model_string_output(self) -> None:
        result = normalize_account_package(
            {
                "account_positioning": "source jade advisor",
                "persona": "trusted seller",
                "target_user_profile": "30-50 year old city buyers",
                "account_names": ["jade advisor"],
                "bios": {"douyin": "source jade selection"},
                "content_columns": ["market tips"],
                "trust_design": ["show certificates"],
                "conversion_path": ["ask for private message"],
                "platform_strategies": {"douyin": "short video leads"},
            }
        )

        self.assertEqual(
            result.target_user_profile,
            {"summary": "30-50 year old city buyers"},
        )

    def test_persona_dict_and_nested_names_are_normalized(self) -> None:
        result = normalize_account_package(
            {
                "account_positioning": {"summary": "source jade advisor"},
                "persona": {"identity": "seller", "style": "direct"},
                "target_user_profile": {"age": "30-50"},
                "account_names": [["name one", "name two"], "name three"],
                "bios": {"douyin": {"text": "source jade"}},
                "content_columns": ["market tips"],
                "trust_design": ["show certificates"],
                "conversion_path": ["ask for private message"],
                "platform_strategies": {"douyin": "short video leads"},
            }
        )

        self.assertIn('"identity": "seller"', result.persona)
        self.assertEqual(result.account_names, ["name one", "name two", "name three"])
        self.assertIn('"text": "source jade"', result.bios["douyin"])

    def test_structured_content_columns_are_preserved(self) -> None:
        content_column = {
            "name": "market stories",
            "description": "source market selection process",
            "frequency": "weekly",
            "examples": ["price comparison", "buyer diary"],
        }

        result = normalize_account_package(
            {
                "account_positioning": "source jade advisor",
                "persona": "trusted seller",
                "target_user_profile": {"age": "30-50"},
                "account_names": ["jade advisor"],
                "bios": {"douyin": "source jade"},
                "content_columns": [content_column],
                "trust_design": ["show certificates"],
                "conversion_path": ["ask for private message"],
                "platform_strategies": {"douyin": "short video leads"},
            }
        )

        self.assertEqual(result.content_columns, [content_column])


if __name__ == "__main__":
    unittest.main()
