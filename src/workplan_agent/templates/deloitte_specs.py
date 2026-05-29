"""Load Deloitte WBS/RAID template structure for LLM prompts and validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_SPECS_DIR = Path(__file__).resolve().parent / "deloitte"
WBS_SPEC_PATH = _SPECS_DIR / "wbs_template.spec.json"
RAID_SPEC_PATH = _SPECS_DIR / "raid_template.spec.json"


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


def format_wbs_spec_for_prompt(spec: dict[str, Any] | None = None) -> str:
    spec = spec or load_wbs_spec()
    lines = [
        "## APS1049 WBS template (authoritative structure)",
        "",
        spec.get("summary", ""),
        "",
        "### Table columns (use these JSON field names)",
    ]
    for col in spec.get("columns", []):
        lines.append(
            f"- `{col['field']}` — {col['header']} "
            f"({col.get('description', '').strip()})"
        )
    lines.extend(["", "### Hierarchy rules"])
    for rule in spec.get("hierarchy_rules", []):
        lines.append(f"- {rule}")
    lines.extend(["", "### Example rows from template"])
    for row in spec.get("example_rows", [])[:5]:
        lines.append(f"- {json.dumps(row, ensure_ascii=False)}")
    return "\n".join(lines).strip()


def format_raid_spec_for_prompt(spec: dict[str, Any] | None = None) -> str:
    spec = spec or load_raid_spec()
    lines = [
        "## APS1049 RAID template (authoritative structure)",
        "",
        spec.get("summary", ""),
        "",
        "Respond with four arrays matching the Excel template sections:",
        "`risks`, `actions`, `issues`, `decisions` (not a single mixed list).",
        "",
    ]
    for section in spec.get("sections", []):
        lines.append(f"### {section['title']} (`{section['key']}`)")
        lines.append(f"Minimum items: {section.get('minimum', 0)}")
        lines.append("Fields:")
        for field in section.get("fields", []):
            req = "required" if field.get("required") else "optional"
            lines.append(
                f"- `{field['name']}` ({field.get('type', 'string')}, {req}): "
                f"{field.get('description', '')}"
            )
        lines.append("")
    simple = spec.get("simple_view", {})
    if simple:
        lines.append("### Simple log view (single-table summary)")
        lines.append(f"Columns: {', '.join(simple.get('columns', []))}")
    return "\n".join(lines).strip()
