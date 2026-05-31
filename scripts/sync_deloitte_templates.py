#!/usr/bin/env python3
"""Extract WBS/RAID structure from Deloitte docx/xlsx into JSON specs for the LLM."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workplan_agent.files.template_extract import (  # noqa: E402
    extract_raid_spec,
    extract_wbs_spec,
)

OUT_DIR = ROOT / "src" / "workplan_agent" / "templates" / "deloitte"


def main() -> None:
    wbs_sources = [
        ROOT / "APS1049_Team2-WBS Template Explanation.docx",
        OUT_DIR / "wbs_template_explanation.docx",
    ]
    raid_sources = [
        ROOT / "APS1049_Team 2-RAID Log-Template .xlsx",
        OUT_DIR / "raid_log_template.xlsx",
    ]

    wbs_path = next((p for p in wbs_sources if p.is_file()), None)
    raid_path = next((p for p in raid_sources if p.is_file()), None)
    if wbs_path is None:
        raise SystemExit("WBS template docx not found in project root or templates/deloitte/")
    if raid_path is None:
        raise SystemExit("RAID template xlsx not found in project root or templates/deloitte/")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    wbs_spec = extract_wbs_spec(wbs_path)
    raid_spec = extract_raid_spec(raid_path)

    (OUT_DIR / "wbs_template.spec.json").write_text(
        json.dumps(wbs_spec, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (OUT_DIR / "raid_template.spec.json").write_text(
        json.dumps(raid_spec, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUT_DIR / 'wbs_template.spec.json'}")
    print(f"Wrote {OUT_DIR / 'raid_template.spec.json'}")


if __name__ == "__main__":
    main()
