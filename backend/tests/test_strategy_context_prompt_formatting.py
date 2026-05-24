import unittest

from app.models.account_strategy_context import AccountStrategyContext
from app.models.project import Project
from app.prompts.execution_plan_prompt import build_execution_plan_prompts
from app.prompts.script_prompt import build_script_prompts
from app.prompts.topic_prompt import build_topic_prompts
from app.models.topic import Topic


def sample_project() -> Project:
    return Project(
        id=1,
        project_name="jade account",
        industry="jewelry",
        sub_industry="jade",
        product="jade bracelet",
        personal_intro="seller",
        target_audience="buyers",
        platforms=["douyin"],
        current_stage="stable",
    )


def structured_strategy_context() -> AccountStrategyContext:
    return AccountStrategyContext(
        id=1,
        project_id=1,
        account_positioning="source market advisor",
        persona="trusted seller",
        target_user_profile={},
        account_names=["jade advisor"],
        bios={},
        content_columns=[
            {
                "name": "market log",
                "description": "source market observations",
                "frequency": "twice weekly",
            },
            "buyer questions",
        ],
        trust_design=["show real market"],
        conversion_path=["comment budget"],
        platform_strategies={"douyin": "strong hook"},
        trust_points=[],
        monetization_paths=[],
        context_data={},
    )


class StrategyContextPromptFormattingTest(unittest.TestCase):
    def test_execution_plan_prompt_accepts_structured_content_columns(self) -> None:
        _, user_prompt = build_execution_plan_prompts(
            sample_project(),
            structured_strategy_context(),
            "30 days",
            "2 hours",
        )

        self.assertIn("market log", user_prompt)
        self.assertIn("buyer questions", user_prompt)

    def test_topic_prompt_accepts_structured_content_columns(self) -> None:
        _, user_prompt = build_topic_prompts(
            sample_project(),
            structured_strategy_context(),
            "douyin",
            "lead generation",
            "video",
            3,
        )

        self.assertIn("market log", user_prompt)
        self.assertIn("buyer questions", user_prompt)

    def test_script_prompt_accepts_structured_content_columns(self) -> None:
        topic = Topic(
            id=1,
            project_id=1,
            title="how to choose jade",
            content_type="tips",
            platform="douyin",
            goal="lead generation",
            score=80,
            topic_data={},
        )

        _, user_prompt = build_script_prompts(
            sample_project(),
            topic,
            structured_strategy_context(),
            "douyin",
            "聊观点",
            "60秒",
            "lead generation",
        )

        self.assertIn("market log", user_prompt)
        self.assertIn("buyer questions", user_prompt)


if __name__ == "__main__":
    unittest.main()
