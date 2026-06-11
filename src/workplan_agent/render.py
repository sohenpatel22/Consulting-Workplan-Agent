import json
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from workplan_agent.display_values import display_cell
from workplan_agent.models.brief import ParsedBrief
from workplan_agent.models.raid import RAIDLog
from workplan_agent.models.session import SessionStatus, WorkplanSession
from workplan_agent.models.wbs import WBS
from workplan_agent.models.raci import RaciLetter, RaciMatrix
from workplan_agent.models.status_report import WeeklyStatusReport
from workplan_agent.models.quality_gates import QualityGateItem, QualityGates

TEMPLATES_DIR = Path(__file__).parent / "templates"
_TEMPLATE_ENV: Environment | None = None


def _cell_filter(value: object, note: str = "") -> str:
    return display_cell(value, note=note.strip() or None)


def _confirmed_marker(item: object) -> str:
    return "*" if getattr(item, "from_confirmed_answer", False) else ""


def _assumed_marker(item: object) -> str:
    return "~" if getattr(item, "is_assumed", False) else ""


def _has_confirmed_items(items: object) -> bool:
    if not isinstance(items, list):
        return False
    return any(getattr(item, "from_confirmed_answer", False) for item in items)


def _has_assumed_items(items: object) -> bool:
    if not isinstance(items, list):
        return False
    return any(getattr(item, "is_assumed", False) for item in items)


def _env() -> Environment:
    global _TEMPLATE_ENV
    if _TEMPLATE_ENV is None:
        env = Environment(
            loader=FileSystemLoader(TEMPLATES_DIR),
            autoescape=select_autoescape(["html"]),
        )
        env.filters["cell"] = _cell_filter
        env.filters["confirmed_marker"] = _confirmed_marker
        env.filters["assumed_marker"] = _assumed_marker
        _TEMPLATE_ENV = env
    return _TEMPLATE_ENV


def render_wbs_markdown(wbs: WBS, parsed_brief: ParsedBrief) -> str:
    template = _env().get_template("wbs.md.j2")
    return template.render(
        wbs=wbs,
        client_name=parsed_brief.client_name,
        project_title=parsed_brief.project_title,
        has_confirmed_items=_has_confirmed_items(wbs.work_packages),
        has_assumed_items=_has_assumed_items(wbs.work_packages),
    )


def render_wbs_html(wbs: WBS, parsed_brief: ParsedBrief) -> str:
    template = _env().get_template("wbs.html.j2")
    return template.render(
        wbs=wbs,
        client_name=parsed_brief.client_name,
        project_title=parsed_brief.project_title,
        has_confirmed_items=_has_confirmed_items(wbs.work_packages),
        has_assumed_items=_has_assumed_items(wbs.work_packages),
    )


def render_raid_markdown(raid: RAIDLog, parsed_brief: ParsedBrief) -> str:
    template = _env().get_template("raid.md.j2")
    all_items = [*raid.risks, *raid.actions, *raid.issues, *raid.decisions]
    return template.render(
        raid=raid,
        client_name=parsed_brief.client_name,
        project_title=parsed_brief.project_title,
        has_confirmed_items=_has_confirmed_items(all_items),
        has_assumed_items=_has_assumed_items(all_items),
    )


def render_raid_html(raid: RAIDLog, parsed_brief: ParsedBrief) -> str:
    template = _env().get_template("raid.html.j2")
    all_items = [*raid.risks, *raid.actions, *raid.issues, *raid.decisions]
    return template.render(
        raid=raid,
        client_name=parsed_brief.client_name,
        project_title=parsed_brief.project_title,
        has_confirmed_items=_has_confirmed_items(all_items),
        has_assumed_items=_has_assumed_items(all_items),
    )


def render_raci_markdown(raci_matrix: RaciMatrix, parsed_brief: ParsedBrief) -> str:
    template = _env().get_template("raci.md.j2")
    return template.render(
        raci_matrix=raci_matrix,
        client_name=parsed_brief.client_name,
        project_title=parsed_brief.project_title,
        has_confirmed_items=_has_confirmed_items(raci_matrix.rows),
        has_assumed_items=_has_assumed_items(raci_matrix.rows),
    )


def render_raci_html(raci_matrix: RaciMatrix, parsed_brief: ParsedBrief) -> str:
    template = _env().get_template("raci.html.j2")
    return template.render(
        raci_matrix=raci_matrix,
        client_name=parsed_brief.client_name,
        project_title=parsed_brief.project_title,
        has_confirmed_items=_has_confirmed_items(raci_matrix.rows),
        has_assumed_items=_has_assumed_items(raci_matrix.rows),
    )


def render_status_markdown(status_report: WeeklyStatusReport, parsed_brief: ParsedBrief) -> str:
    template = _env().get_template("status_report.md.j2")
    return template.render(
        status_report=status_report,
        client_name=parsed_brief.client_name,
        project_title=parsed_brief.project_title,
        has_confirmed_items=_has_confirmed_items(status_report.milestones),
        has_assumed_items=_has_assumed_items(status_report.milestones),
    )


def render_status_html(status_report: WeeklyStatusReport, parsed_brief: ParsedBrief) -> str:
    template = _env().get_template("status_report.html.j2")
    return template.render(
        status_report=status_report,
        client_name=parsed_brief.client_name,
        project_title=parsed_brief.project_title,
        has_confirmed_items=_has_confirmed_items(status_report.milestones),
        has_assumed_items=_has_assumed_items(status_report.milestones),
    )


def generate_quality_gates(session: WorkplanSession) -> QualityGates:
    from workplan_agent.artifact_links import validate_owner_alignment

    items = []
    
    # --- WBS Checks ---
    # 1. WBS Hierarchical Code Validity
    wbs_codes_ok = True
    wbs_code_msg = "All level-2 packages have valid level-1 parent codes."
    if session.wbs:
        level1_codes = {wp.wbs_code for wp in session.wbs.work_packages if wp.level == 1}
        invalid_parents = []
        for wp in session.wbs.work_packages:
            if wp.level == 2:
                if not wp.parent_wbs_code or wp.parent_wbs_code not in level1_codes:
                    invalid_parents.append(f"{wp.wbs_code} (parent: {wp.parent_wbs_code})")
        if invalid_parents:
            wbs_codes_ok = False
            wbs_code_msg = f"Invalid parent codes detected for packages: {', '.join(invalid_parents)}"
    else:
        wbs_codes_ok = False
        wbs_code_msg = "No WBS artifact found to validate."
        
    items.append(QualityGateItem(
        category="WBS",
        title="Hierarchical Code Validity",
        description="Verify every level-2 package has a parent code matching a level-1 package.",
        passed=wbs_codes_ok,
        message=wbs_code_msg,
        manual=False
    ))

    # 2. WBS Deliverable Completeness
    deliverables_ok = True
    deliverables_msg = "All leaf work packages define a key deliverable."
    if session.wbs:
        parent_codes = {wp.parent_wbs_code for wp in session.wbs.work_packages if wp.parent_wbs_code}
        leaf_packages = [wp for wp in session.wbs.work_packages if wp.wbs_code not in parent_codes]
        missing = [wp.wbs_code for wp in leaf_packages if not wp.key_deliverable or not wp.key_deliverable.strip()]
        if missing:
            deliverables_ok = False
            deliverables_msg = f"Leaf packages missing key deliverables: {', '.join(missing)}"
    else:
        deliverables_ok = False
        deliverables_msg = "WBS not generated."

    items.append(QualityGateItem(
        category="WBS",
        title="Deliverable Completeness",
        description="Confirm that every leaf work package specifies concrete, checkable deliverables rather than vague activities.",
        passed=deliverables_ok,
        message=deliverables_msg,
        manual=False
    ))

    # 3. WBS Dependency Alignment
    dependency_ok = True
    dependency_msg = "No dependency loops detected in WBS packages."
    if session.wbs:
        adj = {wp.wbs_code: wp.dependencies for wp in session.wbs.work_packages}
        visited = {}
        def has_cycle(u):
            visited[u] = 1
            for v in adj.get(u, []):
                if v not in visited:
                    visited[v] = 0
                if visited[v] == 1:
                    return True
                if visited[v] == 0:
                    if has_cycle(v):
                        return True
            visited[u] = 2
            return False
        
        for code in adj:
            visited[code] = 0
        for code in adj:
            if visited[code] == 0:
                if has_cycle(code):
                    dependency_ok = False
                    dependency_msg = "Dependency loop detected in WBS packages."
                    break
    else:
        dependency_ok = False
        dependency_msg = "WBS not generated."

    items.append(QualityGateItem(
        category="WBS",
        title="Dependency Alignment",
        description="Ensure that dependencies do not create logical loops and correspond to the project timeline.",
        passed=dependency_ok,
        message=dependency_msg,
        manual=False
    ))
    
    # 4. Resource/Owner Roles
    owners_ok = True
    owner_msg = "All work packages have assigned owners."
    if session.wbs:
        missing_owners = [wp.wbs_code for wp in session.wbs.work_packages if not wp.owner]
        if missing_owners:
            owners_ok = False
            owner_msg = f"Packages missing owners: {', '.join(missing_owners)}"
    else:
        owners_ok = False
        owner_msg = "WBS not generated."
        
    items.append(QualityGateItem(
        category="WBS",
        title="Owner Role Allocation",
        description="Ensure all work packages have owners and align with standard consulting roles (e.g. EM, BA, Architect).",
        passed=owners_ok,
        message=owner_msg,
        manual=True
    ))

    # 5. Duration Realism
    items.append(QualityGateItem(
        category="WBS",
        title="Duration Realism",
        description="Verify task durations are realistic based on client timeline constraints.",
        passed=True if session.wbs else False,
        message="Review durations and task sequencing." if session.wbs else "WBS not generated.",
        manual=True
    ))

    # --- RAID Checks ---
    # 6. RAID risk & action links to WBS
    raid_links_ok = True
    raid_link_msg = "All RAID risks and actions map to valid WBS codes."
    if session.raid and session.wbs:
        wbs_codes = {wp.wbs_code for wp in session.wbs.work_packages}
        invalid_links = []
        for risk in session.raid.risks:
            for link in (risk.wbs_links or []):
                if link not in wbs_codes:
                    invalid_links.append(f"Risk {risk.id} -> {link}")
        for action in session.raid.actions:
            for link in (action.wbs_links or []):
                if link not in wbs_codes:
                    invalid_links.append(f"Action {action.id} -> {link}")
        if invalid_links:
            raid_links_ok = False
            raid_link_msg = f"Invalid links found: {', '.join(invalid_links)}"
    elif not session.raid:
        raid_links_ok = False
        raid_link_msg = "RAID log not generated."

    items.append(QualityGateItem(
        category="RAID",
        title="WBS Link Mapping",
        description="Verify every Risk and Action entry maps to one or more valid WBS codes.",
        passed=raid_links_ok,
        message=raid_link_msg,
        manual=False
    ))

    # 7. RAID Owner Assignment
    raid_owners_ok = True
    raid_owners_msg = "All RAID entries have a valid owner assigned."
    if session.raid:
        missing = []
        for entry in session.raid.risks:
            if not entry.owner or entry.owner.strip().upper() in ("TBD", "UNASSIGNED", ""):
                missing.append(f"Risk {entry.id}")
        for entry in session.raid.actions:
            if not entry.owner or entry.owner.strip().upper() in ("TBD", "UNASSIGNED", ""):
                missing.append(f"Action {entry.id}")
        for entry in session.raid.issues:
            if not entry.owner or entry.owner.strip().upper() in ("TBD", "UNASSIGNED", ""):
                missing.append(f"Issue {entry.id}")
        for entry in session.raid.decisions:
            if not entry.owner or entry.owner.strip().upper() in ("TBD", "UNASSIGNED", ""):
                missing.append(f"Decision {entry.id}")
        if missing:
            raid_owners_ok = False
            raid_owners_msg = f"RAID entries missing owners: {', '.join(missing)}"
    else:
        raid_owners_ok = False
        raid_owners_msg = "RAID log not generated."

    items.append(QualityGateItem(
        category="RAID",
        title="Owner Assignment",
        description="Verify that all Risks, Actions, Issues, and Decisions have a valid owner assigned.",
        passed=raid_owners_ok,
        message=raid_owners_msg,
        manual=False
    ))

    # 8. Risk vs Issue classification
    items.append(QualityGateItem(
        category="RAID",
        title="Risk vs Issue Classification",
        description="Verify that uncertain events are classified as Risks and active problems as Issues.",
        passed=True if session.raid else False,
        message="Review RAID log entries for future uncertainty vs. present active issues." if session.raid else "RAID log not generated.",
        manual=True
    ))

    # --- RACI Checks ---
    # 9. Accountability Coverage
    raci_ok = True
    raci_msg = "Each activity has exactly one Accountable (A) assignment."
    if session.raci_matrix:
        invalid_rows: list[str] = []
        for row in session.raci_matrix.rows:
            accountable = [
                role
                for role, letter in row.assignments.items()
                if letter == RaciLetter.ACCOUNTABLE
            ]
            if len(accountable) != 1:
                invalid_rows.append(row.activity)
        if invalid_rows:
            raci_ok = False
            raci_msg = (
                "Activities without exactly one Accountable (A): "
                + ", ".join(invalid_rows[:3])
            )
        elif len(session.raci_matrix.rows) < 3:
            raci_ok = False
            raci_msg = "RACI matrix should include at least three activity rows."
    else:
        raci_ok = False
        raci_msg = "RACI matrix not generated."

    items.append(QualityGateItem(
        category="RACI",
        title="Accountability Coverage",
        description="Verify each deliverable/activity has exactly one Accountable (A) role.",
        passed=raci_ok,
        message=raci_msg,
        manual=False
    ))

    # 10. RACI Task Coverage
    raci_coverage_ok = True
    raci_coverage_msg = "All level-2 and level-3 WBS packages are represented in the RACI matrix."
    if session.wbs and session.raci_matrix:
        raci_codes = {row.wbs_code for row in session.raci_matrix.rows if row.wbs_code}
        missing_packages = []
        for wp in session.wbs.work_packages:
            if wp.level in (2, 3) and wp.wbs_code not in raci_codes:
                missing_packages.append(wp.wbs_code)
        if missing_packages:
            raci_coverage_ok = False
            raci_coverage_msg = f"WBS packages missing from RACI: {', '.join(missing_packages)}"
    elif not session.wbs:
        raci_coverage_ok = False
        raci_coverage_msg = "WBS not generated."
    else:
        raci_coverage_ok = False
        raci_coverage_msg = "RACI matrix not generated."

    items.append(QualityGateItem(
        category="RACI",
        title="RACI Task Coverage",
        description="Verify each level-2 and level-3 WBS work package is represented as a task in the RACI matrix.",
        passed=raci_coverage_ok,
        message=raci_coverage_msg,
        manual=False
    ))

    # 11. RACI Role Alignment
    raci_align_ok = True
    raci_align_msg = "WBS owners align with RACI assignments."
    if session.wbs and session.raci_matrix:
        issues = validate_owner_alignment(session.wbs, session.raci_matrix)
        if issues:
            raci_align_ok = False
            raci_align_msg = f"Owner misalignments: {', '.join(issues)}"
    elif not session.wbs:
        raci_align_ok = False
        raci_align_msg = "WBS not generated."
    else:
        raci_align_ok = False
        raci_align_msg = "RACI matrix not generated."

    items.append(QualityGateItem(
        category="RACI",
        title="RACI Role Alignment",
        description="Verify WBS task owners align with Responsible (R) or Accountable (A) roles in the RACI matrix.",
        passed=raci_align_ok,
        message=raci_align_msg,
        manual=False
    ))

    # --- Status Checks ---
    # 12. Milestone Synchronization
    milestones_ok = True
    milestones_msg = "Status report milestones are synchronized with timeline objectives."
    if session.status_report and session.parsed_brief:
        brief_milestones = session.parsed_brief.timeline.milestones if session.parsed_brief.timeline else []
        report_milestones = {m.name.lower() for m in session.status_report.milestones}
        missing = [m for m in brief_milestones if m.lower() not in report_milestones]
        if missing:
            milestones_ok = False
            milestones_msg = f"Milestones missing from status report: {', '.join(missing)}"
    elif not session.status_report:
        milestones_ok = False
        milestones_msg = "Weekly status report not generated."

    items.append(QualityGateItem(
        category="Status",
        title="Milestone Synchronization",
        description="Verify that status report milestones match the key milestones in the brief.",
        passed=milestones_ok,
        message=milestones_msg,
        manual=False
    ))

    # 13. RAG Status Justification
    items.append(QualityGateItem(
        category="Status",
        title="RAG Status Justification",
        description="Verify overall project RAG status (Green, Amber, Red) matches the risk log context.",
        passed=True if session.status_report else False,
        message="Review RAG status alignment." if session.status_report else "Weekly status report not generated.",
        manual=True
    ))

    return QualityGates(items=items)


def render_quality_gates_markdown(quality_gates: QualityGates, parsed_brief: ParsedBrief | None = None) -> str:
    lines = [
        "# Quality Gates & Verification Checklist",
        "",
        f"**Project:** {parsed_brief.project_title if parsed_brief else ''}",
        f"**Client:** {parsed_brief.client_name if parsed_brief else ''}",
        "",
        "This checklist tracks automated check outcomes and manual inspection tasks required before project approval.",
        ""
    ]
    
    categories = ["WBS", "RAID", "RACI", "Status"]
    for cat in categories:
        lines.append(f"## {cat} Quality Gates")
        lines.append("")
        cat_items = [item for item in quality_gates.items if item.category == cat]
        for item in cat_items:
            status_symbol = "🟢 PASSED" if item.passed else ("🔴 FAILED" if not item.manual else "🟡 REVIEW REQUIRED")
            box = "[x]" if (item.passed and not item.manual) else "[ ]"
            lines.append(f"### {box} {item.title}")
            lines.append(f"- **Verification Instruction**: {item.description}")
            lines.append(f"- **Status Check**: {status_symbol}")
            if item.message:
                lines.append(f"- **Feedback**: {item.message}")
            lines.append("")
            
    return "\n".join(lines)


def save_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(data, "model_dump"):
        content = data.model_dump(mode="json")
    else:
        content = data
    path.write_text(json.dumps(content, indent=2, default=str), encoding="utf-8")


def save_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def save_quality_gates(output_dir: Path, session: WorkplanSession) -> None:
    if session.parsed_brief is None:
        raise ValueError("Session has no parsed brief.")
    session.quality_gates = generate_quality_gates(session)
    save_json(output_dir / "quality_gates.json", session.quality_gates)
    save_text(
        output_dir / "quality_gates.md",
        render_quality_gates_markdown(session.quality_gates, session.parsed_brief),
    )


def save_artifacts(
    output_dir: Path,
    session: WorkplanSession,
    *,
    refresh_quality_gates: bool = True,
) -> None:
    if session.parsed_brief is None:
        raise ValueError("Session has no parsed brief.")

    save_json(output_dir / "parsed_brief.json", session.parsed_brief)

    if refresh_quality_gates:
        save_quality_gates(output_dir, session)

    if session.wbs is not None:
        save_json(output_dir / "wbs.json", session.wbs)
        save_text(
            output_dir / "wbs.md",
            render_wbs_markdown(session.wbs, session.parsed_brief),
        )
        try:
            from workplan_agent.files.deloitte_export import export_wbs_deloitte_docx

            docx_path = output_dir / "wbs.docx"
            docx_path.parent.mkdir(parents=True, exist_ok=True)
            docx_path.write_bytes(
                export_wbs_deloitte_docx(session.wbs, session.parsed_brief)
            )
        except RuntimeError:
            pass

    if session.raid is not None:
        save_json(output_dir / "raid.json", session.raid)
        save_text(
            output_dir / "raid.md",
            render_raid_markdown(session.raid, session.parsed_brief),
        )
        try:
            from workplan_agent.files.deloitte_export import export_raid_deloitte_xlsx

            xlsx_path = output_dir / "raid.xlsx"
            xlsx_path.parent.mkdir(parents=True, exist_ok=True)
            xlsx_path.write_bytes(
                export_raid_deloitte_xlsx(session.raid, session.parsed_brief)
            )
        except (FileNotFoundError, RuntimeError):
            pass

    if session.raci_matrix is not None:
        save_json(output_dir / "raci_matrix.json", session.raci_matrix)
        save_text(
            output_dir / "raci_matrix.md",
            render_raci_markdown(session.raci_matrix, session.parsed_brief),
        )
        try:
            from workplan_agent.files.deloitte_export import export_raci_deloitte_xlsx

            xlsx_path = output_dir / "raci.xlsx"
            xlsx_path.parent.mkdir(parents=True, exist_ok=True)
            xlsx_path.write_bytes(
                export_raci_deloitte_xlsx(session.raci_matrix, session.parsed_brief)
            )
        except (FileNotFoundError, RuntimeError):
            pass

    if session.status_report is not None:
        save_json(output_dir / "status_report.json", session.status_report)
        save_text(
            output_dir / "status_report.md",
            render_status_markdown(session.status_report, session.parsed_brief),
        )


def save_version_snapshot(output_dir: Path, session: WorkplanSession, version: int) -> None:
    if session.parsed_brief is None:
        return
    version_dir = output_dir / "versions" / f"v{version}"
    
    if session.quality_gates is not None:
        save_json(version_dir / "quality_gates.json", session.quality_gates)
        save_text(
            version_dir / "quality_gates.md",
            render_quality_gates_markdown(session.quality_gates, session.parsed_brief),
        )

    if session.wbs is not None:
        save_json(version_dir / "wbs.json", session.wbs)
        save_text(
            version_dir / "wbs.md",
            render_wbs_markdown(session.wbs, session.parsed_brief),
        )
    if session.raid is not None:
        save_json(version_dir / "raid.json", session.raid)
        save_text(
            version_dir / "raid.md",
            render_raid_markdown(session.raid, session.parsed_brief),
        )
    if session.raci_matrix is not None:
        save_json(version_dir / "raci_matrix.json", session.raci_matrix)
        save_text(
            version_dir / "raci_matrix.md",
            render_raci_markdown(session.raci_matrix, session.parsed_brief),
        )
    if session.status_report is not None:
        save_json(version_dir / "status_report.json", session.status_report)
        save_text(
            version_dir / "status_report.md",
            render_status_markdown(session.status_report, session.parsed_brief),
        )


def save_status(output_dir: Path, session: WorkplanSession) -> None:
    parsed = session.parsed_brief
    status = {
        "session_id": session.session_id,
        "brief_path": session.brief_path,
        "status": session.status.value,
        "revision_count": session.revision_count,
        "version_count": len(session.versions),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "client": parsed.client_name if parsed else "",
            "project": parsed.project_title if parsed else "",
            "objectives_count": len(parsed.objectives) if parsed else 0,
            "wbs_items": len(session.wbs.work_packages) if session.wbs else 0,
            "raid_risks": len(session.raid.risks) if session.raid else 0,
            "raid_actions": len(session.raid.actions) if session.raid else 0,
            "raid_issues": len(session.raid.issues) if session.raid else 0,
            "raid_decisions": len(session.raid.decisions) if session.raid else 0,
            "raci_activities_count": len(session.raci_matrix.rows) if session.raci_matrix else 0,
            "status_milestones_count": len(session.status_report.milestones) if session.status_report else 0,
            "quality_gates_passed": sum(1 for i in session.quality_gates.items if i.passed) if session.quality_gates else 0,
            "quality_gates_total": len(session.quality_gates.items) if session.quality_gates else 0,
            "open_questions": parsed.open_questions if parsed else [],
        },
    }
    save_json(output_dir / "status.json", status)
