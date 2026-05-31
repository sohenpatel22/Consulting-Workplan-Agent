from workplan_agent.models.wbs import WBS
from workplan_agent.templates.deloitte_specs import build_wbs_generation_contract, load_wbs_spec


def test_wbs_generation_contract_includes_full_spec() -> None:
    spec = load_wbs_spec()
    contract = build_wbs_generation_contract(spec)
    for rule in spec["hierarchy_rules"]:
        assert rule in contract
    for row in spec["example_rows"]:
        assert row["wbs_code"] in contract
    assert "work_packages" in contract
    assert "authoritative" in contract.lower()


def test_wbs_accepts_minimal_structure_without_hierarchy_gate() -> None:
    """Parsing accepts JSON shape; Deloitte rules are prompt-driven, not post-validated."""
    wbs = WBS.model_validate(
        {
            "work_packages": [
                {
                    "level": 1,
                    "wbs_code": "1.0",
                    "wbs_element_title": "Only phase",
                    "description_scope": "Scope",
                    "key_deliverable": "Deliverable",
                }
            ]
        }
    )
    assert len(wbs.work_packages) == 1


def test_wbs_normalizes_parent_code_stem_to_phase() -> None:
    wbs = WBS.model_validate(
        {
            "work_packages": [
                {
                    "level": 1,
                    "wbs_code": "1.0",
                    "wbs_element_title": "Phase",
                    "description_scope": "",
                    "key_deliverable": "",
                },
                {
                    "level": 2,
                    "wbs_code": "1.1",
                    "parent_wbs_code": "1",
                    "wbs_element_title": "Stream",
                    "description_scope": "",
                    "key_deliverable": "",
                },
            ]
        }
    )
    child = next(wp for wp in wbs.work_packages if wp.wbs_code == "1.1")
    assert child.parent_wbs_code == "1.0"
