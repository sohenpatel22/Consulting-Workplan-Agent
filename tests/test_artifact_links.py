from workplan_agent.artifact_links import (
    derive_raci_roles_from_wbs,
    reconcile_raci_matrix,
    reconcile_raid_log,
    validate_owner_alignment,
    validate_raid_owner_alignment,
    validate_wbs_raci_coverage,
)
from workplan_agent.llm.fixtures import RACI_MATRIX_FIXTURE, RAID_FIXTURE, WBS_FIXTURE
from workplan_agent.models.raci import RaciLetter, RaciMatrix
from workplan_agent.models.raid import RAIDLog
from workplan_agent.models.wbs import WBS


def test_raci_roles_derived_from_wbs_owners() -> None:
    wbs = WBS.model_validate(WBS_FIXTURE)
    assert derive_raci_roles_from_wbs(wbs) == [
        "Deloitte Delivery Lead",
        "Data Engineering Lead",
        "Client CIO",
    ]


def test_reconcile_raci_columns_match_wbs_owners_only() -> None:
    wbs = WBS.model_validate(WBS_FIXTURE)
    raci = RaciMatrix.model_validate(
        {
            "roles": ["Engagement Sponsor (CMO)", "Deloitte Delivery Lead"],
            "rows": [
                {
                    "wbs_code": "1.1",
                    "activity": "Stakeholder interviews",
                    "assignments": {
                        "Engagement Sponsor (CMO)": "A",
                        "Deloitte Delivery Lead": "R",
                    },
                }
            ],
        }
    )
    reconciled = reconcile_raci_matrix(wbs, raci)
    assert reconciled.roles == derive_raci_roles_from_wbs(wbs)
    assert "Engagement Sponsor (CMO)" not in reconciled.roles
    row = next(r for r in reconciled.rows if r.wbs_code == "1.1")
    assert "Engagement Sponsor (CMO)" not in row.assignments


def test_reconcile_raci_adds_wbs_codes_and_owner_roles() -> None:
    wbs = WBS.model_validate(WBS_FIXTURE)
    raci = RaciMatrix.model_validate(
        {
            "roles": ["Deloitte Delivery Lead"],
            "rows": [
                {
                    "activity": "Stakeholder interviews",
                    "assignments": {"Deloitte Delivery Lead": "R"},
                }
            ],
        }
    )
    reconciled = reconcile_raci_matrix(wbs, raci)
    row = next(r for r in reconciled.rows if r.wbs_code == "1.1")
    assert row.assignments["Deloitte Delivery Lead"] == RaciLetter.RESPONSIBLE
    assert "Data Engineering Lead" in reconciled.roles


def test_reconcile_raid_owner_from_raci_r() -> None:
    wbs = WBS.model_validate(WBS_FIXTURE)
    raci = RaciMatrix.model_validate(RACI_MATRIX_FIXTURE)
    raid = RAIDLog.model_validate(
        {
            **RAID_FIXTURE,
            "risks": [
                {
                    **RAID_FIXTURE["risks"][0],
                    "owner": "Wrong Owner",
                },
                *RAID_FIXTURE["risks"][1:],
            ],
        }
    )
    reconciled = reconcile_raid_log(wbs, raci, raid)
    assert reconciled.risks[0].owner == "Deloitte Delivery Lead"


def test_fixture_passes_cross_artifact_validation() -> None:
    wbs = WBS.model_validate(WBS_FIXTURE)
    raci = RaciMatrix.model_validate(RACI_MATRIX_FIXTURE)
    raid = RAIDLog.model_validate(RAID_FIXTURE)
    assert not validate_wbs_raci_coverage(wbs, raci)
    assert not validate_owner_alignment(wbs, raci)
    assert not validate_raid_owner_alignment(wbs, raci, raid)
