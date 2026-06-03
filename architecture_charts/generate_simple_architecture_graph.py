#!/usr/bin/env python3
"""Generate a clear left-to-right architecture diagram for non-technical readers.

Writes:
  - ARCHITECTURE_SIMPLE.mmd
  - ARCHITECTURE_SIMPLE.md

Run from repo root:
  uv run python generate_simple_architecture_graph.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
OUTPUT_MMD = REPO_ROOT / "ARCHITECTURE_SIMPLE.mmd"
OUTPUT_MD = REPO_ROOT / "ARCHITECTURE_SIMPLE.md"

SIMPLE_OVERVIEW = r"""flowchart LR
    subgraph inputs["LEFT: Inputs from the client / user"]
        direction TB
        BRIEF["Client brief<br/>(background, objectives, scope,<br/>timeline, constraints)"]
        GUIDE["Optional guidance<br/>(focus areas, tone,<br/>assumptions, formatting needs)"]
        ANSWERS["Clarifying answers<br/>(used when the brief is incomplete)"]
        FEEDBACK["Review feedback<br/>(per artifact: WBS, RAID,<br/>stakeholder, status)"]
    end

    subgraph entry["How work enters the system"]
        direction TB
        WEB["Web app<br/>(upload / review)"]
        CLI["Command line<br/>(batch run)"]
        API["FastAPI service<br/>(session endpoints)"]
    end

    subgraph system["MIDDLE: Workplan Agent system"]
        direction TB
        ORCH["OrchestratorAgent<br/><br/>Controls the workflow<br/>Keeps the session state<br/>Decides the next step"]
        SESSION["WorkplanSession<br/><br/>Shared working memory:<br/>parsed brief, WBS, RAID,<br/>stakeholder map, status report"]

        subgraph agents["Specialist agents"]
            direction TB
            PARSER["Brief Parser<br/>turns brief into structured facts"]
            WBS_AGENT["WBS Generator<br/>builds tasks and milestones"]
            RAID_AGENT["RAID Generator<br/>builds risks, assumptions,<br/>issues, decisions"]
            STAKE_AGENT["Stakeholder Generator<br/>builds engagement map"]
            STATUS_AGENT["Status Generator<br/>builds weekly report"]
            REVISION_AGENT["Revision Agent<br/>applies reviewer feedback"]
        end

        LLM["LLM routing layer<br/><br/>Sends structured prompts to<br/>OpenAI or Anthropic and expects<br/>structured JSON back"]
        SAVE["Save / version outputs<br/><br/>Writes artifacts, status.json,<br/>and revision snapshots"]
    end

    subgraph outputs["RIGHT: Outputs / reports"]
        direction TB
        PARSED["Parsed brief<br/>(structured project summary)"]
        WBS_OUT["Work Breakdown Structure<br/>(work packages, activities,<br/>milestones, owners)"]
        RAID_OUT["RAID log<br/>(risks, assumptions,<br/>issues, decisions)"]
        STAKE_OUT["Stakeholder map<br/>(roles, influence, engagement)"]
        STATUS_OUT["Weekly status report<br/>(RAG status, milestones,<br/>risks, next steps)"]
        QUALITY_OUT["Quality gates<br/>(checks and review checklist)"]
        EXPORTS["Downloadable files<br/>(Word, Excel, Markdown,<br/>PDF / HTML where available)"]
    end

    BRIEF --> WEB
    BRIEF --> CLI
    GUIDE --> WEB
    GUIDE --> CLI
    ANSWERS --> API
    FEEDBACK -.->|"revision request"| API

    WEB --> API
    CLI --> ORCH
    API --> ORCH

    ORCH <-->|"reads / updates"| SESSION
    ORCH -->|"1. parse brief"| PARSER
    PARSER -->|"structured facts"| SESSION
    PARSER <-->|"LLM messages"| LLM

    ORCH -->|"2. generate WBS"| WBS_AGENT
    SESSION -->|"parsed brief"| WBS_AGENT
    WBS_AGENT -->|"WBS"| SESSION
    WBS_AGENT <-->|"LLM messages"| LLM

    ORCH -->|"3. generate RAID"| RAID_AGENT
    SESSION -->|"parsed brief + WBS"| RAID_AGENT
    RAID_AGENT -->|"RAID log"| SESSION
    RAID_AGENT <-->|"LLM messages"| LLM

    ORCH -->|"4. generate supporting reports"| STAKE_AGENT
    ORCH -->|"4. generate supporting reports"| STATUS_AGENT
    SESSION -->|"brief + WBS + RAID"| STAKE_AGENT
    SESSION -->|"brief + WBS + RAID"| STATUS_AGENT
    STAKE_AGENT -->|"stakeholder map"| SESSION
    STATUS_AGENT -->|"status report"| SESSION
    STAKE_AGENT <-->|"LLM messages"| LLM
    STATUS_AGENT <-->|"LLM messages"| LLM

    ORCH -->|"5. revise if requested"| REVISION_AGENT
    SESSION -->|"current reports + feedback"| REVISION_AGENT
    REVISION_AGENT -->|"updated reports"| SESSION
    REVISION_AGENT <-->|"LLM messages"| LLM

    SESSION --> SAVE
    SAVE --> PARSED
    SAVE --> WBS_OUT
    SAVE --> RAID_OUT
    SAVE --> STAKE_OUT
    SAVE --> STATUS_OUT
    SAVE --> QUALITY_OUT
    SAVE --> EXPORTS
"""

SIMPLE_STEPS = r"""flowchart LR
    A["1. Start<br/><br/>Client brief + optional guidance"]
    B["2. Understand<br/><br/>Brief parser extracts<br/>project facts and open questions"]
    C["3. Build<br/><br/>Specialist agents create<br/>WBS, RAID, stakeholder map,<br/>and status report"]
    D["4. Review<br/><br/>User reviews outputs<br/>and sends feedback"]
    E["5. Finalize<br/><br/>Approved reports and<br/>downloadable files"]

    A --> B --> C --> D --> E
    D -.->|"revision feedback"| C

    classDef endpoint fill:#eef7ff,stroke:#2b6cb0,stroke-width:2px
    class A,E endpoint
"""


def build_mermaid_document() -> str:
    return "\n".join(
        [
            "%% Workplan Agent — simple overview (generated)",
            "%% Regenerate: uv run python generate_simple_architecture_graph.py",
            "",
            SIMPLE_OVERVIEW.strip(),
            "",
            "%% ---",
            "",
            SIMPLE_STEPS.strip(),
            "",
        ]
    )


def build_markdown_wrapper() -> str:
    return "\n".join(
        [
            "# Workplan Agent — Combined Business Overview",
            "",
            "A more detailed plain-language view that keeps **inputs on the left** "
            "and **outputs on the right**, while still showing the main orchestration pieces. "
            "For full technical detail, see [`ARCHITECTURE.md`](ARCHITECTURE.md).",
            "",
            "Auto-generated by [`generate_simple_architecture_graph.py`](generate_simple_architecture_graph.py).",
            "",
            "## Inputs → Orchestration → Reports",
            "",
            "```mermaid",
            SIMPLE_OVERVIEW.strip(),
            "```",
            "",
            "## Business Journey",
            "",
            "```mermaid",
            SIMPLE_STEPS.strip(),
            "```",
            "",
            "### In plain language",
            "",
            "1. **Start** — The user provides the client brief, optional guidance, and later any clarifying answers or review feedback.",
            "2. **Orchestrate** — `OrchestratorAgent` controls the workflow and keeps all intermediate results in `WorkplanSession`.",
            "3. **Generate** — Specialist agents create the WBS, RAID log, stakeholder map, and weekly status report through structured LLM calls.",
            "4. **Revise** — Feedback goes through the revision flow and updates only the requested reports.",
            "5. **Deliver** — The system saves versioned artifacts and exports reports for download.",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print Mermaid to stdout instead of writing files",
    )
    args = parser.parse_args()

    mermaid = build_mermaid_document()

    if args.stdout:
        print(mermaid, end="")
        return

    OUTPUT_MMD.write_text(mermaid, encoding="utf-8")
    OUTPUT_MD.write_text(build_markdown_wrapper(), encoding="utf-8")
    print(f"Wrote {OUTPUT_MMD.relative_to(REPO_ROOT)}")
    print(f"Wrote {OUTPUT_MD.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
