from workplan_agent.templates.deloitte_specs import (
    build_raci_generation_contract,
    build_raid_generation_contract,
    build_status_report_generation_contract,
    build_wbs_generation_contract,
    load_raci_spec,
    load_raid_spec,
    load_status_report_spec,
    load_wbs_spec,
    raci_json_output_instruction,
    raid_json_output_instruction,
    status_json_output_instruction,
    wbs_json_output_instruction,
)


def test_wbs_spec_loaded() -> None:
    spec = load_wbs_spec()
    fields = {col["field"] for col in spec["columns"]}
    assert "wbs_code" in fields
    assert "key_deliverable" in fields
    assert "owner_side" not in fields


def test_raid_spec_sections_match_template() -> None:
    spec = load_raid_spec()
    keys = {section["key"] for section in spec["sections"]}
    assert keys == {"risks", "actions", "issues", "decisions"}
    for section in spec["sections"]:
        assert any(field["name"] == "owner_side" for field in section["fields"])


def test_raci_spec_matches_template() -> None:
    spec = load_raci_spec()
    assert spec.get("roles")
    assert spec.get("example_rows")
    assert spec["activity_column"] == "Deliverable / Activity"


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
    raci_prompt = build_raci_generation_contract()
    status_prompt = build_status_report_generation_contract()
    assert "wbs_code" in wbs_prompt
    assert "owner_side" not in wbs_prompt
    assert "owner" in wbs_prompt
    assert "generation contract" in wbs_prompt.lower()
    assert "risks" in raid_prompt
    assert "Actions" in raid_prompt
    assert "owner_side" in raid_prompt
    assert "mitigation" in raid_prompt.lower()
    assert "duplicate" in raid_prompt.lower()
    assert "WRONG" in raid_prompt
    assert "one action per risk mitigation" in raid_prompt.lower()
    assert "roles" in raci_prompt
    assert "Deliverable / Activity" in raci_prompt
    assert "holds the pen" in raci_prompt.lower()
    assert "milestones" in status_prompt
    assert "owner_side" in status_prompt
    assert "target_date" in status_prompt
    assert "TBD" in status_prompt
    assert wbs_json_output_instruction()
    assert raid_json_output_instruction()
    assert raci_json_output_instruction()
    assert status_json_output_instruction()
