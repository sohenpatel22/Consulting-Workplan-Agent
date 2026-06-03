"""Load Deloitte template specs and build LLM generation contracts from them."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_SPECS_DIR = Path(__file__).resolve().parent / "deloitte"
WBS_SPEC_PATH = _SPECS_DIR / "wbs_template.spec.json"
RAID_SPEC_PATH = _SPECS_DIR / "raid_template.spec.json"
STAKEHOLDER_SPEC_PATH = _SPECS_DIR / "stakeholder_template.spec.json"
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


def load_stakeholder_spec() -> dict[str, Any]:
    if not STAKEHOLDER_SPEC_PATH.is_file():
        raise FileNotFoundError(f"Stakeholder template spec missing: {STAKEHOLDER_SPEC_PATH}")
    return _read_json(STAKEHOLDER_SPEC_PATH)


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
            "- Classify `owner_side` as Client, Consultant, or Joint for every work package.",
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
        lines.append("- Fields per item:")
        for field in section.get("fields", []):
            req = "required" if field.get("required") else "optional"
            desc = field.get("description", "").strip()
            suffix = f" — {desc}" if desc else ""
            lines.append(
                f"  - `{field['name']}` ({field.get('type', 'string')}, {req}){suffix}"
            )
        lines.append("")

    simple = spec.get("simple_view", {})
    if simple:
        lines.append("### Simple log view (for exports)")
        lines.append(f"Columns: {', '.join(simple.get('columns', []))}")
        lines.append("")

    lines.extend(
        [
            "### Pre-submit checklist",
            "- Every risk and action includes `wbs_links` pointing to real `wbs_code` values from the WBS.",
            "- Every RAID item includes `owner_side`: Client, Consultant, or Joint.",
            "- Risks include `mitigation` and `probability` (High, Moderate, or Low).",
            "- Use `priority` (and `probability` for risks): High, Moderate, or Low.",
            "- Derive actions from assumptions, client activities, and follow-ups in the brief.",
            "",
            "### Content alignment",
            "- Ground items in the parsed brief and WBS; do not invent unrelated risks.",
        ]
    )
    return "\n".join(lines).strip()


def wbs_json_output_instruction() -> str:
    return (
        "Respond with **valid JSON only** (no markdown fences or commentary). "
        "The Deloitte WBS generation contract above defines the required shape, fields, "
        "and hierarchy — follow it exactly.\n"
        'Root object: `{"work_packages": [ ... ]}`'
    )


def raid_json_output_instruction() -> str:
    return (
        "Respond with **valid JSON only** (no markdown fences or commentary). "
        "The Deloitte RAID generation contract above defines the required sections, fields, "
        "and minimums — follow it exactly.\n"
        'Root object: `{"risks": [], "actions": [], "issues": [], "decisions": []}`'
    )


def format_wbs_spec_for_prompt(spec: dict[str, Any] | None = None) -> str:
    """Alias for the WBS generation contract (used in tests and docs)."""
    return build_wbs_generation_contract(spec)


def format_raid_spec_for_prompt(spec: dict[str, Any] | None = None) -> str:
    """Alias for the RAID generation contract (used in tests and docs)."""
    return build_raid_generation_contract(spec)


def build_stakeholder_generation_contract(spec: dict[str, Any] | None = None) -> str:
    """Full Deloitte Stakeholder Map contract from stakeholder_template.spec.json."""
    spec = spec or load_stakeholder_spec()
    lines = [
        "## Deloitte Stakeholder Map generation contract (authoritative — follow while generating)",
        "",
        spec.get("summary", ""),
        "",
        "Generate the complete stakeholder map in one response. Each table row is one object "
        "in `stakeholders`.",
        "",
        "### Required JSON envelope",
        '{"stakeholders": [ /* one object per stakeholder row */ ]}',
        "",
        "### Table columns (use these JSON field names on every row)",
    ]
    for col in spec.get("columns", []):
        lines.append(
            f"- `{col['field']}` — **{col['header']}**: {col.get('description', '').strip()}"
        )

    lines.extend(["", "### Generation rules"])
    for rule in spec.get("generation_rules", []):
        lines.append(f"- {rule}")

    lines.extend(
        [
            "",
            "### Example rows from the Deloitte template (mirror depth and engagement style)",
        ]
    )
    for row in spec.get("example_rows", []):
        lines.append(f"- {json.dumps(row, ensure_ascii=False)}")

    lines.extend(
        [
            "",
            "### Content alignment",
            "- Ground every stakeholder in the parsed brief, WBS, or RAID.",
            "- Infer at most 3–5 stakeholders; each inferred row needs a specific rationale.",
            "- Classify `organization_side` as Client, Consultant, Joint, or Other.",
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
            "### Content alignment",
            "- Do not invent progress not supported by WBS or RAID.",
            "- Pull risks from RAID; blockers from open RAID issues or WBS dependencies.",
            "- Classify each milestone `owner_side` as Client, Consultant, or Joint.",
        ]
    )
    return "\n".join(lines).strip()


def stakeholder_json_output_instruction() -> str:
    return (
        "Respond with **valid JSON only** (no markdown fences or commentary). "
        "The Deloitte Stakeholder Map generation contract above defines the required shape "
        "and fields — follow it exactly.\n"
        'Root object: `{"stakeholders": [ ... ]}`'
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


def format_stakeholder_spec_for_prompt(spec: dict[str, Any] | None = None) -> str:
    return build_stakeholder_generation_contract(spec)


def format_status_report_spec_for_prompt(spec: dict[str, Any] | None = None) -> str:
    return build_status_report_generation_contract(spec)
