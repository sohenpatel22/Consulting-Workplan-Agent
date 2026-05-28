from workplan_agent.agents.brief_parser import BriefParserAgent
from workplan_agent.agents.wbs_generator import WBSGeneratorAgent
from workplan_agent.config import get_settings
from workplan_agent.llm.caching import cached_block, flatten_content, has_cached_blocks
from workplan_agent.llm.mock_provider import MockLLMProvider
from workplan_agent.models.brief import Objective, ParsedBrief
from workplan_agent.models.wbs import WBS
from workplan_agent.prompts import (
    WBS_REQUIREMENTS,
    revision_user_blocks,
    wbs_generator_system_blocks,
)


def test_cached_blocks_marked() -> None:
    blocks = wbs_generator_system_blocks(WBS)
    assert any("cache_control" in block for block in blocks)
    assert WBS_REQUIREMENTS in blocks[1]["text"]


def test_brief_parser_builds_cached_messages(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_PROMPT_CACHE", "true")
    import workplan_agent.config as config_module

    config_module._settings = None

    agent = BriefParserAgent(MockLLMProvider())
    messages = agent.build_messages(brief_text="Sample brief")
    assert has_cached_blocks(messages)
    assert isinstance(messages[0]["content"], list)
    assert isinstance(messages[1]["content"], list)


def test_revision_user_splits_context_and_feedback() -> None:
    blocks = revision_user_blocks(
        task="Revise the WBS",
        parsed_brief_json='{"client_name": "Acme"}',
        wbs_json='{"work_packages": []}',
        raid_json='{"items": []}',
        feedback="Add more detail to 1.1",
    )
    assert "cache_control" in blocks[0]
    assert "cache_control" not in blocks[1]
    assert "Add more detail" in blocks[1]["text"]


def test_flatten_content_joins_blocks() -> None:
    text = flatten_content([cached_block("A"), cached_block("B")])
    assert text == "A\n\nB"


def test_caching_disabled_falls_back_to_strings(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_PROMPT_CACHE", "false")
    import workplan_agent.config as config_module

    config_module._settings = None

    agent = WBSGeneratorAgent(MockLLMProvider())
    messages = agent.build_messages(
        parsed_brief=ParsedBrief(
            client_name="Acme",
            project_title="Test",
            objectives=[Objective(id="1", description="Goal")],
            scope_in=["Item"],
        )
    )
    assert isinstance(messages[0]["content"], str)
    assert isinstance(messages[1]["content"], str)
    assert get_settings().enable_prompt_cache is False
