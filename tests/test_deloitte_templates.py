from workplan_agent.templates.deloitte_specs import (
    format_raid_spec_for_prompt,
    format_wbs_spec_for_prompt,
    load_raid_spec,
    load_wbs_spec,
)


def test_wbs_spec_loaded() -> None:
    spec = load_wbs_spec()
    fields = {col["field"] for col in spec["columns"]}
    assert "wbs_code" in fields
    assert "key_deliverable" in fields


def test_raid_spec_sections_match_template() -> None:
    spec = load_raid_spec()
    keys = {section["key"] for section in spec["sections"]}
    assert keys == {"risks", "actions", "issues", "decisions"}


def test_prompt_includes_template_structure() -> None:
    wbs_prompt = format_wbs_spec_for_prompt()
    raid_prompt = format_raid_spec_for_prompt()
    assert "wbs_code" in wbs_prompt
    assert "risks" in raid_prompt
    assert "Actions" in raid_prompt
