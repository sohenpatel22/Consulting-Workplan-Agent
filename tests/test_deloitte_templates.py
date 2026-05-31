from workplan_agent.templates.deloitte_specs import (
    build_raid_generation_contract,
    build_wbs_generation_contract,
    load_raid_spec,
    load_wbs_spec,
    raid_json_output_instruction,
    wbs_json_output_instruction,
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


def test_generation_contracts_include_template_structure() -> None:
    wbs_prompt = build_wbs_generation_contract()
    raid_prompt = build_raid_generation_contract()
    assert "wbs_code" in wbs_prompt
    assert "generation contract" in wbs_prompt.lower()
    assert "risks" in raid_prompt
    assert "Actions" in raid_prompt
    assert wbs_json_output_instruction()
    assert raid_json_output_instruction()
