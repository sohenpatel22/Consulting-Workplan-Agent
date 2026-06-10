"""Load Deloitte template specs and build LLM generation contracts from them."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_SPECS_DIR = Path(__file__).resolve().parent / "deloitte"
WBS_SPEC_PATH = _SPECS_DIR / "wbs_template.spec.json"
RAID_SPEC_PATH = _SPECS_DIR / "raid_template.spec.json"
RACI_SPEC_PATH = _SPECS_DIR / "raci_template.spec.json"
STATUS_SPEC_PATH = _SPECS_DIR / "status_report_template.spec.json"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_wbs_spec() -> dict[str, Any]:
    if not WBS_SPEC_PATH.is_file():
        raise FileNotFoundError(f"WBS template spec missing: {WBS_SPEC_PATH}")
    return _read_json(WBS_SPEC_PATH)


def load_raid_spec() -> dict[str, Any]:
    if not RAID_SPEC_PATH.is_file():
        raise FileNotFoundError(f"RAID template spec missing: {RAID_SPEC_PATH}")
    return _read_json(RAID_SPEC_PATH)


def load_raci_spec() -> dict[str, Any]:
    if not RACI_SPEC_PATH.is_file():
        raise FileNotFoundError(f"RACI template spec missing: {RACI_SPEC_PATH}")
    return _read_json(RACI_SPEC_PATH)


def load_status_report_spec() -> dict[str, Any]:
    if not STATUS_SPEC_PATH.is_file():
        raise FileNotFoundError(f"Status report template spec missing: {STATUS_SPEC_PATH}")
    return _read_json(STATUS_SPEC_PATH)


def build_wbs_generation_contract(spec: dict[str, Any] | None = None) -> str:
    """Full Deloitte WBS contract for the LLM — single source of truth from wbs_template.spec.json."""
    spec = spec or load_wbs_spec()
    lines = [
        "## Deloitte WBS generation contract (authoritative — follow while generating)",
        "",
        spec.get("summary", ""),
        "",
        "Generate the complete WBS in one response. Each table row is one object in `work_packages`.",
        "Do not emit a separate `phases` list or alternate structure.",
        "",
        "### Required JSON envelope",
        '{"work_packages": [ /* one object per WBS row */ ]}',
        "",
        "### Table columns (use these JSON field names on every row)",
    ]
    for col in spec.get("columns", []):
        lines.append(
            f"- `{col['field']}` — **{col['header']}**: {col.get('description', '').strip()}"
        )

    lines.extend(["", "### Hierarchy rules (apply while building work_packages)"])
    for rule in spec.get("hierarchy_rules", []):
        lines.append(f"- {rule}")

    generation_rules = spec.get("generation_rules", [])
    if generation_rules:
        lines.extend(["", "### Generation rules"])
        for rule in generation_rules:
            lines.append(f"- {rule}")

    lines.extend(
        [
            "",
            "### Example rows from the Deloitte template (mirror this depth and linking)",
        ]
    )
    for row in spec.get("example_rows", []):
        lines.append(f"- {json.dumps(row, ensure_ascii=False)}")

    lines.extend(
        [
            "",
            "### Pre-submit checklist",
            "Before you finish, confirm your JSON satisfies every hierarchy rule above,",
            "uses only field names from the column list, and links `parent_wbs_code` /",
            "`dependencies` to `wbs_code` values that exist in the same `work_packages` array.",
            "",
            "### Content alignment",
            "- Map work to objectives and in-scope items from the parsed brief.",
            "- Exclude out-of-scope work.",
            "- Use client terminology from the brief in titles and descriptions.",
            "- Set `owner` to the named role or person who will hold R in RACI (use the same label as a RACI column header).",
            "- Every `wbs_code` is the unique ID that links RACI rows, RAID wbs_links, and status milestones.",
            "- When confirmed open-question answers are provided, set `from_confirmed_answer` "
            "to true on rows that directly implement those answers; otherwise false.",
            "- **Minimise assumptions**: only populate a field when the brief (or confirmed answers) "
            "provides the information. Leave optional fields at their defaults rather than inventing detail.",
            "- Set `is_assumed: true` on any row where you had to assume a key value "
            "(e.g. owner, duration, scope) not stated or clearly implied by the brief. "
            "Set `is_assumed: false` otherwise.",
        ]
    )
    return "\n".join(lines).strip()


def build_raid_generation_contract(spec: dict[str, Any] | None = None) -> str:
    """Full Deloitte RAID contract for the LLM — single source of truth from raid_template.spec.json."""
    spec = spec or load_raid_spec()
    lines = [
        "## Deloitte RAID generation contract (authoritative — follow while generating)",
        "",
        spec.get("summary", ""),
        "",
        "Generate the complete RAID log in one response using exactly four top-level arrays",
        "that match the Excel template sections (not a single mixed `items` list).",
        "",
        "### Required JSON envelope",
        '{"risks": [], "actions": [], "issues": [], "decisions": []}',
        "",
    ]
    for section in spec.get("sections", []):
        minimum = section.get("minimum", 0)
        lines.append(f"### {section['title']} (`{section['key']}`)")
        if minimum:
            lines.append(f"- Include **at least {minimum}** item(s) when the brief supports it.")
        elif section.get("key") == "actions":
            lines.append(
                "- Include actions **only** for discrete follow-up work from the brief "
                "(client prerequisites, assumption validation). **Never** create one action "
                "per risk mitigation — mitigation stays on the risk row."
            )
        lines.append("- Fields per item:")
        for field in section.get("fields", []):
            req = "required" if field.get("required") else "optional"
            desc = field.get("description", "").strip()
            suffix = f" — {desc}" if desc else ""
            lines.append(
                f"  - `{field['name']}` ({field.get('type', 'string')}, {req}){suffix}"
            )
        lines.append("")

    generation_rules = spec.get("generation_rules", [])
    if generation_rules:
        lines.append("### Generation rules")
        for rule in generation_rules:
            lines.append(f"- {rule}")
        lines.append("")

    simple = spec.get("simple_view", {})
    if simple:
        lines.append("### Simple log view (for exports)")
        lines.append(f"Columns: {', '.join(simple.get('columns', []))}")
        lines.append("")

    lines.extend(
        [
            "### Cross-artifact linking (WBS → RACI → RAID)",
            "- WBS `wbs_code` is the thread: every risk and action must include `wbs_links` to affected WBS tasks.",
            "- RAID `owner` must match the RACI Responsible (R) role for the primary linked WBS task "
            "(same person who owns the work in WBS).",
            "",
            "### Pre-submit checklist",
            "- Every risk and action includes `wbs_links` pointing to real `wbs_code` values from the WBS.",
            "- Every risk includes a `mitigation` value (concrete plan or TBD wording when unknown).",
            "- Risks include `probability`, `impact`, `risk_rating`, `risk_appetite`, and response "
            "`priority` (Monitor closely, Monitor, Stay informed, or Respond as required).",
            "- Actions, issues, and decisions use `priority`: High, Moderate, or Low.",
            "- Do not duplicate risk mitigations as separate actions — keep mitigation on the risk row.",
            "- `len(actions)` must not equal `len(risks)` by default; actions are not a mirror of the risks list.",
            "- Derive actions from assumptions, client activities, and follow-ups in the brief.",
            "",
            "### Content alignment",
            "- Ground items in the parsed brief and WBS; do not invent unrelated risks.",
            "- Keep Risks and Actions lists distinct with minimal overlap.",
            "- When confirmed open-question answers are provided, set `from_confirmed_answer` "
            "to true on entries that directly implement those answers; otherwise false.",
            "- **Minimise assumptions**: ground every entry in the brief or upstream artifacts. "
            "Do not invent details (probabilities, owners, timelines) that are not stated or implied.",
            "- Set `is_assumed: true` on any entry where you had to assume a key value "
            "not stated or clearly implied by the brief. Set `is_assumed: false` otherwise.",
        ]
    )
    return "\n".join(lines).strip()


def wbs_json_output_instruction() -> str:
    return (
        "Respond with **valid JSON only** (no markdown fences or commentary). "
        "The WBS generation contract above defines the required shape, fields, "
        "and hierarchy — follow it exactly.\n"
        'Root object: `{"work_packages": [ ... ]}`'
    )


def raid_json_output_instruction() -> str:
    return (
        "Respond with **valid JSON only** (no markdown fences or commentary). "
        "The RAID generation contract above defines the required sections, fields, "
        "and minimums — follow it exactly.\n"
        'Root object: `{"risks": [], "actions": [], "issues": [], "decisions": []}`\n'
        "Put every mitigation plan on the matching risk row. Do not add parallel actions "
        "that restate those mitigations."
    )


def format_wbs_spec_for_prompt(spec: dict[str, Any] | None = None) -> str:
    """Alias for the WBS generation contract (used in tests and docs)."""
    return build_wbs_generation_contract(spec)


def format_raid_spec_for_prompt(spec: dict[str, Any] | None = None) -> str:
    """Alias for the RAID generation contract (used in tests and docs)."""
    return build_raid_generation_contract(spec)


def build_raci_generation_contract(spec: dict[str, Any] | None = None) -> str:
    """Full Deloitte RACI contract from raci_template.spec.json."""
    spec = spec or load_raci_spec()
    wbs_code_col = spec.get("wbs_code_column", "WBS Code")
    activity_col = spec.get("activity_column", "Task / Activity")
    lines = [
        "## Deloitte RACI generation contract (authoritative — follow while generating)",
        "",
        spec.get("summary", ""),
        "",
        "WBS is the foundation. Each RACI row maps to one WBS task via `wbs_code`. "
        "Column headers are **dynamic**: set `roles` to the distinct `owner` values from "
        "the WBS (same strings as the WBS Owner column). The WBS owner for each task must hold R or A.",
        "",
        "Generate the complete RACI matrix in one response. Column headers go in `roles`; "
        "each WBS task is one object in `rows`.",
        "",
        "### Required JSON envelope",
        '{"roles": [ /* distinct WBS owner strings, first-seen order */ ], "rows": [ /* one per WBS task */ ]}',
        "",
        f"### Row identifier: **{wbs_code_col}** (`wbs_code` in JSON — must match WBS)",
        f"### Task column: **{activity_col}** (`activity` in JSON — WBS element title)",
        "",
        "### Role columns (dynamic — derived from WBS `owner` field)",
        "- Collect every distinct non-empty `owner` from `work_packages` into `roles`.",
        "- Do not invent column headers that are not WBS owners.",
        "- RAID `owner` must use the same strings as WBS owners / RACI columns.",
    ]
    assignment_values = spec.get("assignment_values", ["R", "A", "C", "I"])
    lines.extend(
        [
            "",
            f"### Assignment values: {', '.join(assignment_values)}",
            "",
            "### Generation rules",
        ]
    )
    for rule in spec.get("generation_rules", []):
        lines.append(f"- {rule}")

    lines.extend(
        [
            "",
            "### Example rows (illustrative — your `roles` must match the WBS owners provided)",
        ]
    )
    for row in spec.get("example_rows", []):
        lines.append(f"- {json.dumps(row, ensure_ascii=False)}")

    lines.extend(
        [
            "",
            "### Content alignment",
            "- Column headers (`roles`) must be exactly the distinct WBS owner values — no extra stakeholders.",
            "- One row per level-3 WBS work package; every row must include the matching `wbs_code`.",
            "- WBS `owner` for each task must appear as R or A in that row's assignments.",
            "- Each row must have exactly one Accountable (A) assignment.",
            "- Use R for who holds the pen; C for parties supporting the Responsible role.",
            "- When confirmed open-question answers are provided, set `from_confirmed_answer` "
            "to true on rows that directly implement those answers; otherwise false.",
            "- **Minimise assumptions**: derive assignments solely from the WBS and brief. "
            "Do not assign roles that cannot be inferred from the brief.",
            "- Set `is_assumed: true` on any row where you had to assume an assignment "
            "not clearly supported by the WBS or brief. Set `is_assumed: false` otherwise.",
        ]
    )
    return "\n".join(lines).strip()


def build_status_report_generation_contract(spec: dict[str, Any] | None = None) -> str:
    """Full Deloitte Weekly Status Report contract from status_report_template.spec.json."""
    spec = spec or load_status_report_spec()
    lines = [
        "## Deloitte Weekly Status Report generation contract (authoritative — follow while generating)",
        "",
        spec.get("summary", ""),
        "",
        "### Required JSON envelope",
        '{"project_name": "...", "project_manager": "...", "date": "...", '
        '"summary": "...", "new_initiatives": [], "blockers": [], "risks": [], '
        '"milestones": [], "supporting_links": []}',
        "",
        "### Header fields",
    ]
    for field in spec.get("header_fields", []):
        lines.append(
            f"- `{field['field']}` — **{field['label']}**: {field.get('description', '').strip()}"
        )

    lines.extend(["", "### Report sections"])
    for section in spec.get("sections", []):
        lines.append(
            f"- `{section['field']}` ({section['label']}): {section.get('description', '').strip()}"
        )

    lines.extend(["", "### Milestone table columns"])
    for col in spec.get("milestone_columns", []):
        lines.append(
            f"- `{col['field']}` — **{col['header']}**: {col.get('description', '').strip()}"
        )
    status_values = spec.get("milestone_status_values", [])
    if status_values:
        lines.append(f"- `status` must be one of: {', '.join(status_values)}.")

    lines.extend(["", "### Generation rules"])
    for rule in spec.get("generation_rules", []):
        lines.append(f"- {rule}")

    example_milestones = spec.get("example_milestones", [])
    if example_milestones:
        lines.extend(["", "### Example milestone rows"])
        for row in example_milestones:
            lines.append(f"- {json.dumps(row, ensure_ascii=False)}")

    lines.extend(
        [
            "",
            "### Cross-artifact linking (pull from WBS, RACI, and RAID)",
            "- Progress and milestones: trace to WBS tasks and their schedule status.",
            "- Accountability: reference who reports what using RACI R/A holders for in-flight WBS tasks.",
            "- Escalations: surface high-priority RAID risks and open issues linked to WBS work packages.",
            "",
            "### Content alignment",
            "- Do not invent progress not supported by WBS or RAID.",
            "- Pull risks from RAID; blockers from open RAID issues or WBS dependencies.",
            "- Milestones must reflect the WBS delivery plan with concrete target dates — avoid TBD unless unavoidable.",
            "- Set each milestone `owner_side` to the accountable party for that milestone.",
            "- When confirmed open-question answers are provided, set `from_confirmed_answer` "
            "to true on milestones that directly implement those answers; otherwise false.",
            "- **Minimise assumptions**: milestones must be traceable to WBS tasks or brief objectives. "
            "Do not invent dates or owners not stated or derivable from the artifacts.",
            "- Set `is_assumed: true` on any milestone where you had to assume a target date, "
            "owner, or status not stated in the brief or WBS. Set `is_assumed: false` otherwise.",
        ]
    )
    return "\n".join(lines).strip()


def raci_json_output_instruction() -> str:
    return (
        "Respond with **valid JSON only** (no markdown fences or commentary). "
        "The Deloitte RACI generation contract above defines the required shape "
        "and fields — follow it exactly.\n"
        'Root object: `{"roles": [ ... ], "rows": [ ... ]}`'
    )


def status_json_output_instruction() -> str:
    return (
        "Respond with **valid JSON only** (no markdown fences or commentary). "
        "The Deloitte Weekly Status Report generation contract above defines the required "
        "sections and fields — follow it exactly.\n"
        'Root object: `{"project_name": "...", "project_manager": "...", "date": "...", '
        '"summary": "...", "new_initiatives": [], "blockers": [], "risks": [], '
        '"milestones": [], "supporting_links": []}`'
    )


def format_raci_spec_for_prompt(spec: dict[str, Any] | None = None) -> str:
    return build_raci_generation_contract(spec)


def format_status_report_spec_for_prompt(spec: dict[str, Any] | None = None) -> str:
    return build_status_report_generation_contract(spec)
