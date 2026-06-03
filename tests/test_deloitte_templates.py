from workplan_agent.templates.deloitte_specs import (
    build_raid_generation_contract,
    build_stakeholder_generation_contract,
    build_status_report_generation_contract,
    build_wbs_generation_contract,
    load_raid_spec,
    load_stakeholder_spec,
    load_status_report_spec,
    load_wbs_spec,
    raid_json_output_instruction,
    stakeholder_json_output_instruction,
    status_json_output_instruction,
    wbs_json_output_instruction,
)


def test_wbs_spec_loaded() -> None:
    spec = load_wbs_spec()
    fields = {col["field"] for col in spec["columns"]}
    assert "wbs_code" in fields
    assert "key_deliverable" in fields
    assert "owner_side" in fields


def test_raid_spec_sections_match_template() -> None:
    spec = load_raid_spec()
    keys = {section["key"] for section in spec["sections"]}
    assert keys == {"risks", "actions", "issues", "decisions"}
    for section in spec["sections"]:
        assert any(field["name"] == "owner_side" for field in section["fields"])


def test_stakeholder_spec_columns_match_template() -> None:
    spec = load_stakeholder_spec()
    fields = {col["field"] for col in spec["columns"]}
    assert "name" in fields
    assert "organization_side" in fields
    assert "engagement_strategy" in fields
    assert spec.get("example_rows")


def test_status_report_spec_sections_match_template() -> None:
    spec = load_status_report_spec()
    fields = {section["field"] for section in spec["sections"]}
    assert "summary" in fields
    assert "milestones" in fields
    milestone_fields = {col["field"] for col in spec["milestone_columns"]}
    assert "owner_side" in milestone_fields


def test_generation_contracts_include_template_structure() -> None:
    wbs_prompt = build_wbs_generation_contract()
    raid_prompt = build_raid_generation_contract()
    stakeholder_prompt = build_stakeholder_generation_contract()
    status_prompt = build_status_report_generation_contract()
    assert "wbs_code" in wbs_prompt
    assert "owner_side" in wbs_prompt
    assert "generation contract" in wbs_prompt.lower()
    assert "risks" in raid_prompt
    assert "Actions" in raid_prompt
    assert "owner_side" in raid_prompt
    assert "stakeholders" in stakeholder_prompt
    assert "organization_side" in stakeholder_prompt
    assert "milestones" in status_prompt
    assert "owner_side" in status_prompt
    assert wbs_json_output_instruction()
    assert raid_json_output_instruction()
    assert stakeholder_json_output_instruction()
    assert status_json_output_instruction()
