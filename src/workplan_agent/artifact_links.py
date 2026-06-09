"""Cross-artifact linking: WBS is the foundation; RACI, RAID, and status trace back to it."""

from __future__ import annotations

from workplan_agent.models.raci import RaciLetter, RaciMatrix, RaciRow
from workplan_agent.models.raid import ActionEntry, IssueEntry, RAIDLog, RiskEntry
from workplan_agent.models.wbs import WBS, WorkPackage


def wbs_codes(wbs: WBS) -> set[str]:
    return {wp.wbs_code for wp in wbs.work_packages}


def raci_row_for_code(raci: RaciMatrix, wbs_code: str) -> RaciRow | None:
    for row in raci.rows:
        if row.wbs_code == wbs_code:
            return row
    return None


def responsible_role(row: RaciRow) -> str | None:
    for role, letter in row.assignments.items():
        if letter == RaciLetter.RESPONSIBLE:
            return role
    return None


def accountable_role(row: RaciRow) -> str | None:
    for role, letter in row.assignments.items():
        if letter == RaciLetter.ACCOUNTABLE:
            return role
    return None


def owner_role_for_wbs_code(wbs: WBS, raci: RaciMatrix, wbs_code: str) -> str | None:
    """Role holding R (preferred) or A for a WBS task — used as RAID owner."""
    row = raci_row_for_code(raci, wbs_code)
    if row is None:
        return None
    return responsible_role(row) or accountable_role(row)


def collect_wbs_owner_roles(wbs: WBS, *, min_level: int = 2) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for wp in wbs.work_packages:
        if wp.level < min_level:
            continue
        owner = wp.owner.strip()
        if owner and owner not in seen:
            seen.add(owner)
            ordered.append(owner)
    return ordered


def _ensure_role_assignments(row: RaciRow, roles: list[str]) -> RaciRow:
    assignments = dict(row.assignments)
    for role in roles:
        assignments.setdefault(role, RaciLetter.INFORMED)
    return row.model_copy(update={"assignments": assignments})


def _set_owner_raci(row: RaciRow, owner: str) -> RaciRow:
    """Ensure the WBS owner holds R or A on this RACI row."""
    if not owner:
        return row
    assignments = dict(row.assignments)
    if owner in assignments:
        current = assignments[owner]
        if current in (RaciLetter.RESPONSIBLE, RaciLetter.ACCOUNTABLE):
            return row
        assignments[owner] = RaciLetter.RESPONSIBLE
        return row.model_copy(update={"assignments": assignments})

    accountable = accountable_role(row)
    if accountable and accountable != owner:
        assignments[accountable] = RaciLetter.CONSULTED
    assignments[owner] = RaciLetter.RESPONSIBLE
    return row.model_copy(update={"assignments": assignments})


def reconcile_raci_matrix(wbs: WBS, raci: RaciMatrix) -> RaciMatrix:
    """Align RACI roles and assignments with WBS owners and task IDs."""
    owner_roles = collect_wbs_owner_roles(wbs)
    roles = list(raci.roles)
    role_set = set(roles)
    for owner in owner_roles:
        if owner not in role_set:
            roles.append(owner)
            role_set.add(owner)

    wbs_by_code = {wp.wbs_code: wp for wp in wbs.work_packages}
    title_to_code = {
        wp.wbs_element_title.strip().lower(): wp.wbs_code
        for wp in wbs.work_packages
    }
    rows_by_code: dict[str, RaciRow] = {}
    extra_rows: list[RaciRow] = []

    def _resolve_wbs_code(row: RaciRow) -> str | None:
        code = row.wbs_code.strip()
        if code in wbs_by_code:
            return code
        title_key = row.activity.strip().lower()
        if title_key in title_to_code:
            return title_to_code[title_key]
        for wp in wbs.work_packages:
            if title_key.startswith(wp.wbs_code):
                return wp.wbs_code
        return None

    for row in raci.rows:
        code = _resolve_wbs_code(row)
        if code:
            wp = wbs_by_code[code]
            activity = row.activity.strip() or wp.wbs_element_title
            updated = row.model_copy(
                update={
                    "wbs_code": code,
                    "activity": activity,
                }
            )
            updated = _ensure_role_assignments(updated, roles)
            updated = _set_owner_raci(updated, wp.owner.strip())
            rows_by_code[code] = updated
        else:
            extra_rows.append(_ensure_role_assignments(row, roles))

    for wp in wbs.work_packages:
        if wp.level < 3:
            continue
        if wp.wbs_code in rows_by_code:
            continue
        assignments = {role: RaciLetter.INFORMED for role in roles}
        owner = wp.owner.strip()
        if owner and owner in assignments:
            assignments[owner] = RaciLetter.RESPONSIBLE
        if not any(letter == RaciLetter.ACCOUNTABLE for letter in assignments.values()):
            for role in roles:
                if role != owner:
                    assignments[role] = RaciLetter.ACCOUNTABLE
                    break
        rows_by_code[wp.wbs_code] = RaciRow(
            wbs_code=wp.wbs_code,
            activity=wp.wbs_element_title,
            assignments=assignments,
        )

    merged_rows = sorted(rows_by_code.values(), key=lambda r: r.wbs_code)
    merged_rows.extend(extra_rows)
    return raci.model_copy(update={"roles": roles, "rows": merged_rows})


def _primary_wbs_link(links: list[str]) -> str | None:
    for link in links:
        code = link.strip()
        if code:
            return code
    return None


def _reconcile_entry_owner(
    owner: str,
    wbs_links: list[str],
    wbs: WBS,
    raci: RaciMatrix,
) -> str:
    primary = _primary_wbs_link(wbs_links)
    if primary is None:
        return owner
    linked_owner = owner_role_for_wbs_code(wbs, raci, primary)
    if linked_owner:
        return linked_owner
    return owner


def reconcile_raid_log(wbs: WBS, raci: RaciMatrix, raid: RAIDLog) -> RAIDLog:
    """Set RAID owners from the RACI Responsible role for the primary linked WBS task."""
    risks = [
        risk.model_copy(
            update={
                "owner": _reconcile_entry_owner(
                    risk.owner, risk.wbs_links, wbs, raci
                )
            }
        )
        for risk in raid.risks
    ]
    actions = [
        action.model_copy(
            update={
                "owner": _reconcile_entry_owner(
                    action.owner, action.wbs_links, wbs, raci
                )
            }
        )
        for action in raid.actions
    ]
    return raid.model_copy(update={"risks": risks, "actions": actions})


def validate_wbs_raci_coverage(wbs: WBS, raci: RaciMatrix) -> list[str]:
    issues: list[str] = []
    raci_codes = {row.wbs_code for row in raci.rows if row.wbs_code}
    for wp in wbs.work_packages:
        if wp.level < 3:
            continue
        if wp.wbs_code not in raci_codes:
            issues.append(f"{wp.wbs_code}: no RACI row for WBS task")
    return issues


def validate_owner_alignment(wbs: WBS, raci: RaciMatrix) -> list[str]:
    issues: list[str] = []
    for wp in wbs.work_packages:
        if wp.level < 2 or not wp.owner.strip():
            continue
        row = raci_row_for_code(raci, wp.wbs_code)
        if row is None:
            continue
        owner = wp.owner.strip()
        letter = row.assignments.get(owner)
        if letter not in (RaciLetter.RESPONSIBLE, RaciLetter.ACCOUNTABLE):
            issues.append(
                f"{wp.wbs_code}: WBS owner '{owner}' lacks R or A in RACI"
            )
    return issues


def validate_raid_owner_alignment(
    wbs: WBS,
    raci: RaciMatrix,
    raid: RAIDLog,
) -> list[str]:
    issues: list[str] = []
    valid_codes = wbs_codes(wbs)

    def _check(entry: RiskEntry | ActionEntry, label: str) -> None:
        for link in entry.wbs_links:
            if link not in valid_codes:
                issues.append(f"{entry.id}: links to unknown WBS code {link}")
        primary = _primary_wbs_link(entry.wbs_links)
        if primary is None:
            issues.append(f"{entry.id}: missing wbs_links")
            return
        expected = owner_role_for_wbs_code(wbs, raci, primary)
        if expected and entry.owner.strip() != expected:
            issues.append(
                f"{entry.id}: owner '{entry.owner}' should be '{expected}' "
                f"(R on WBS {primary})"
            )

    for risk in raid.risks:
        _check(risk, "risk")
    for action in raid.actions:
        _check(action, "action")
    return issues
