#!/usr/bin/env python3
"""Extract WBS/RAID/RACI/Status structure from Deloitte templates into JSON specs."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workplan_agent.files.template_extract import (  # noqa: E402
    extract_raci_spec,
    extract_raid_spec,
    extract_status_report_spec,
    extract_wbs_spec,
)

OUT_DIR = ROOT / "src" / "workplan_agent" / "templates" / "deloitte"


def _first_existing(paths: list[Path]) -> Path | None:
    return next((p for p in paths if p.is_file()), None)


def _copy_template(source: Path, dest: Path) -> None:
    if source.resolve() != dest.resolve():
        shutil.copy2(source, dest)


def main() -> None:
    wbs_sources = [
        ROOT / "APS1049_Team2-WBS Template Explanation.docx",
        OUT_DIR / "wbs_template_explanation.docx",
    ]
    raid_sources = [
        ROOT / "APS1049_Team 2-RAID Log-Template .xlsx",
        OUT_DIR / "raid_log_template.xlsx",
    ]
    raci_sources = [
        ROOT / "APS1049 RACI Template.xlsx",
        OUT_DIR / "raci_template.xlsx",
    ]
    status_sources = [
        ROOT / "APS1049_Team 2-Weekly Status Report.docx",
        OUT_DIR / "status_report_template.docx",
    ]

    wbs_path = _first_existing(wbs_sources)
    raid_path = _first_existing(raid_sources)
    raci_path = _first_existing(raci_sources)
    status_path = _first_existing(status_sources)

    missing = [
        name
        for name, path in (
            ("WBS template docx", wbs_path),
            ("RAID template xlsx", raid_path),
            ("RACI template xlsx", raci_path),
            ("Weekly Status Report template docx", status_path),
        )
        if path is None
    ]
    if missing:
        raise SystemExit("Missing templates: " + ", ".join(missing))

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    wbs_dest = OUT_DIR / "wbs_template_explanation.docx"
    raid_dest = OUT_DIR / "raid_log_template.xlsx"
    raci_dest = OUT_DIR / "raci_template.xlsx"
    status_dest = OUT_DIR / "status_report_template.docx"

    _copy_template(wbs_path, wbs_dest)
    _copy_template(raid_path, raid_dest)
    _copy_template(raci_path, raci_dest)
    _copy_template(status_path, status_dest)

    specs = {
        "wbs_template.spec.json": extract_wbs_spec(wbs_dest),
        "raid_template.spec.json": extract_raid_spec(raid_dest),
        "raci_template.spec.json": extract_raci_spec(raci_dest),
        "status_report_template.spec.json": extract_status_report_spec(status_dest),
    }

    for filename, spec in specs.items():
        path = OUT_DIR / filename
        path.write_text(
            json.dumps(spec, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
