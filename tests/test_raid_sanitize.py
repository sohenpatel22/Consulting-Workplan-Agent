from workplan_agent.models.raid import ActionEntry, RAIDLog, RiskEntry
from workplan_agent.raid_sanitize import action_duplicates_risk_mitigation


def _risk(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "R1",
        "title": "SME availability",
        "description": "Limited SME time may delay assessment",
        "mitigation": "Pre-book workshops on Tue/Thu",
        "wbs_links": ["1.1"],
    }
    base.update(overrides)
    return base


def _action(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "A1",
        "title": "Pre-book SME workshops",
        "description": "Schedule workshops on Tue/Thu",
        "wbs_links": ["1.1"],
    }
    base.update(overrides)
    return base


def test_detects_action_that_restates_mitigation() -> None:
    raid = RAIDLog.model_validate(
        {
            "risks": [_risk(), _risk(id="R2", title="API instability", mitigation="Version-pin APIs"), _risk(id="R3", title="Budget overrun", mitigation="Weekly cost tracking")],
            "actions": [_action()],
        }
    )
    assert len(raid.actions) == 0


def test_keeps_unrelated_prerequisite_action() -> None:
    raid = RAIDLog.model_validate(
        {
            "risks": [
                _risk(),
                _risk(id="R2", title="API instability", mitigation="Version-pin APIs"),
                _risk(id="R3", title="Budget overrun", mitigation="Weekly cost tracking"),
            ],
            "actions": [
                {
                    "id": "A1",
                    "title": "Azure licenses procured",
                    "description": "Client procures Databricks/ADF before build",
                    "wbs_links": ["3.0"],
                }
            ],
        }
    )
    assert len(raid.actions) == 1
    assert raid.actions[0].title == "Azure licenses procured"


def test_detects_mitigation_prefix_action_for_risk() -> None:
    risks = [
        RiskEntry.model_validate(
            _risk(mitigation="TBD — mitigation approach to be defined"),
        )
    ]
    action = ActionEntry.model_validate(
        {"id": "A1", "title": "Mitigate SME availability", "wbs_links": ["1.1"]},
    )
    assert action_duplicates_risk_mitigation(action, risks)


def test_fixture_actions_are_not_mitigation_duplicates() -> None:
    from workplan_agent.llm.fixtures import RAID_FIXTURE

    raid = RAIDLog.model_validate(RAID_FIXTURE)
    assert len(raid.risks) == 3
    assert len(raid.actions) == 2
