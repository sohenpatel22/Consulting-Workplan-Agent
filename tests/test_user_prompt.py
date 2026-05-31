from workplan_agent.agents.brief_parser import BriefParserAgent
from workplan_agent.llm.caching import flatten_content
from workplan_agent.llm.mock_provider import MockLLMProvider
from workplan_agent.prompts import (
    brief_parser_user_blocks,
    build_generation_guidance,
    format_user_instructions,
    normalize_user_prompt,
    wbs_generator_user_blocks,
)


def test_normalize_user_prompt_strips_whitespace() -> None:
    assert normalize_user_prompt("  hello  ") == "hello"
    assert normalize_user_prompt(None) == ""
    assert normalize_user_prompt("   ") == ""


def test_format_user_instructions_empty_when_blank() -> None:
    assert format_user_instructions("") == ""
    assert format_user_instructions(None) == ""


def test_format_user_instructions_includes_guidance() -> None:
    text = format_user_instructions("Focus on integration risks.")
    assert "Planner instructions" in text
    assert "Focus on integration risks." in text
    assert "contradict explicit facts" in text


def test_brief_parser_user_blocks_appends_instructions() -> None:
    blocks = brief_parser_user_blocks("Brief body", "Add UAT phase.")
    content = flatten_content(blocks)
    assert "Brief body" in content
    assert "Add UAT phase." in content
    assert "Planner instructions" in content


def test_brief_parser_user_blocks_omits_instructions_when_empty() -> None:
    blocks = brief_parser_user_blocks("Brief only", "")
    content = flatten_content(blocks)
    assert "Planner instructions" not in content


def test_wbs_generator_user_blocks_appends_instructions() -> None:
    guidance = build_generation_guidance("Use agile names.")
    blocks = wbs_generator_user_blocks('{"client_name": "Acme"}', guidance)
    content = flatten_content(blocks)
    assert "Use agile names." in content
    assert "Planner instructions" in content


def test_brief_parser_forwards_user_prompt_to_messages() -> None:
    agent = BriefParserAgent(MockLLMProvider())
    messages = agent.build_messages(
        brief_text="Sample brief",
        user_prompt="Highlight data migration.",
    )
    user_content = messages[1]["content"]
    if isinstance(user_content, list):
        user_content = flatten_content(user_content)
    assert "Highlight data migration." in user_content
