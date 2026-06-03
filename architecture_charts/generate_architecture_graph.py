#!/usr/bin/env python3
"""Generate Mermaid architecture diagrams for the workplan agent system.

Writes:
  - ARCHITECTURE.mmd   — raw Mermaid (paste into mermaid.live or IDE preview)
  - ARCHITECTURE.md    — Markdown wrapper for GitHub / docs viewers

Run from repo root:
  uv run python generate_architecture_graph.py
  uv run python generate_architecture_graph.py --stdout
"""

from __future__ import annotations

import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
OUTPUT_MMD = REPO_ROOT / "ARCHITECTURE.mmd"
OUTPUT_MD = REPO_ROOT / "ARCHITECTURE.md"

# Specialist agents do not call each other. The orchestrator passes Pydantic
# artifacts in and out of WorkplanSession; each agent only talks to the LLM.
ORCHESTRATION_DIAGRAM = r"""flowchart TB
    subgraph entry["Entry points"]
        CLI["CLI<br/>workplan run"]
        API["FastAPI<br/>POST /api/sessions"]
        WEB["Browser UI<br/>static/app.js"]
    end

    subgraph orch["OrchestratorAgent"]
        direction TB
        O["Orchestrator<br/>(orchestrator.py)"]
        PARSE["parse_brief_only"]
        GEN["generate_workplan_artifacts"]
        REVLOOP["apply_revision<br/>(web API)"]
    end

    subgraph state["Shared session state (orchestrator-owned)"]
        WS["WorkplanSession<br/>parsed_brief, wbs, raid,<br/>stakeholder_map, status_report"]
        DISK["Persistence<br/>save_artifacts / status.json / versions/"]
    end

    subgraph agents["Specialist agents (stateless)"]
        BP["BriefParserAgent"]
        WBS["WBSGeneratorAgent"]
        RAID["RAIDGeneratorAgent"]
        SH["StakeholderMapGeneratorAgent"]
        ST["StatusReportGeneratorAgent"]
        REV["RevisionAgent"]
        subgraph rev_helpers["Revision helpers (internal)"]
            RW["_WBSRevisionHelper"]
            RR["_RAIDRevisionHelper"]
            RSH["_StakeholderRevisionHelper"]
            RST["_StatusRevisionHelper"]
        end
    end

    subgraph llm["LLM layer"]
        RP["RoutingLLMProvider"]
        OAI["OpenAIProvider"]
        ANT["AnthropicProvider"]
    end

    CLI --> O
    WEB --> API
    API --> O

    O <-->|"read / write models"| WS
    WS --> DISK

    O --> PARSE
    O --> GEN
    O --> REVLOOP

    PARSE -->|"brief_text, user_prompt"| BP
    BP -->|"ParsedBrief"| PARSE
    PARSE --> WS

    GEN -->|"parsed_brief + guidance"| WBS
    WBS -->|"WBS"| GEN
    GEN -->|"parsed_brief, wbs"| RAID
    RAID -->|"RAIDLog"| GEN
    GEN -->|"parsed_brief, wbs, raid"| SH
    SH -->|"StakeholderMap"| GEN
    GEN -->|"parsed_brief, wbs, raid"| ST
    ST -->|"WeeklyStatusReport"| GEN
    GEN --> WS

    REVLOOP -->|"artifacts + feedback + target"| REV
    REV --> RW
    REV --> RR
    REV --> RSH
    REV --> RST
    REV -->|"RevisionResult (partial updates)"| REVLOOP
    REVLOOP --> WS

    BP & WBS & RAID & SH & ST & RW & RR & RSH & RST -->|"build_messages()"| RP
    RP -->|"OpenAI model"| OAI
    RP -->|"Anthropic model"| ANT
    OAI & ANT -->|"call_structured → Pydantic"| BP & WBS & RAID & SH & ST & RW & RR & RSH & RST
"""

PIPELINE_SEQUENCE = r"""sequenceDiagram
    autonumber
    actor User
    participant Entry as CLI / API
    participant Orch as OrchestratorAgent
    participant Session as WorkplanSession
    participant Agent as Specialist Agent
    participant LLM as RoutingLLMProvider

    User->>Entry: brief (+ optional user_prompt)
    Entry->>Orch: run_pipeline / run_generation

    Orch->>Agent: BriefParserAgent.run(brief_text)
    Agent->>Agent: build_messages(system, user)
    Agent->>LLM: call_structured(messages, ParsedBrief)
    LLM-->>Agent: ParsedBrief JSON
    Agent-->>Orch: ParsedBrief
    Orch->>Session: session.parsed_brief = ...

    alt open questions (web: pause for confirm)
        Orch-->>Entry: AWAITING_CONFIRMATION
        User->>Entry: resolved answers
        Entry->>Orch: generate_workplan_artifacts
    end

    Orch->>Agent: WBSGeneratorAgent.run(parsed_brief)
    Agent->>LLM: call_structured → WBS
    LLM-->>Agent: WBS
    Agent-->>Orch: WBS
    Orch->>Session: session.wbs = ...

    Orch->>Agent: RAIDGeneratorAgent.run(parsed_brief, wbs)
    Note over Orch,LLM: warm_raid_build_prefix caches Anthropic prefix
    Agent->>LLM: call_structured → RAIDLog
    LLM-->>Agent: RAIDLog
    Orch->>Session: session.raid = ...

    Orch->>Agent: Stakeholder / Status generators (wbs + raid context)
    Orch->>Session: save_artifacts, snapshot v1

    loop review / revision
        User->>Entry: feedback + target (wbs|raid|stakeholder|status)
        Entry->>Orch: apply_revision(session, target, feedback)
        Orch->>Agent: RevisionAgent.run(artifacts, feedback, target)
        Agent->>LLM: structured revision call for selected artifact
        LLM-->>Agent: RevisionResult
        Orch->>Session: merge result, revision_count++, versions/
    end
"""

DATA_FLOW_DIAGRAM = r"""flowchart LR
    subgraph inputs["Inputs passed by orchestrator"]
        BT["brief_text"]
        UP["user_prompt / generation_guidance"]
        PB["ParsedBrief"]
        W["WBS"]
        R["RAIDLog"]
        FB["reviewer feedback"]
    end

    BT --> BP["BriefParserAgent"] --> PB
    PB --> WBS["WBSGeneratorAgent"] --> W
    PB --> W
    W --> RAID["RAIDGeneratorAgent"] --> R
    PB --> R
    W --> SH["StakeholderMapGeneratorAgent"]
    R --> SH
    PB --> ST["StatusReportGeneratorAgent"]
    W --> ST
    R --> ST

    PB --> REV["RevisionAgent"]
    W --> REV
    R --> REV
    FB --> REV
    REV -->|"target=wbs"| W2["updated WBS"]
    REV -->|"target=raid, uses new WBS if revised"| R2["updated RAID"]
    REV --> SH2["updated StakeholderMap"]
    REV --> ST2["updated StatusReport"]
"""

def build_mermaid_document() -> str:
    sections = [
        "%% Workplan Agent — system architecture (generated; do not edit by hand)",
        "%% Regenerate: uv run python generate_architecture_graph.py",
        "",
        "---",
        "title: Orchestration & agent wiring",
        "---",
        ORCHESTRATION_DIAGRAM.strip(),
        "",
        "---",
        "title: Generation & revision sequence",
        "---",
        PIPELINE_SEQUENCE.strip(),
        "",
        "---",
        "title: Artifact data dependencies",
        "---",
        DATA_FLOW_DIAGRAM.strip(),
    ]
    return "\n".join(sections) + "\n"


def build_markdown_wrapper(mermaid: str) -> str:
    return "\n".join(
        [
            "# Workplan Agent — Architecture Diagrams",
            "",
            "Auto-generated by [`generate_architecture_graph.py`](generate_architecture_graph.py).",
            "Re-run after orchestration or agent changes.",
            "",
            "## Orchestration & agent wiring",
            "",
            "```mermaid",
            ORCHESTRATION_DIAGRAM.strip(),
            "```",
            "",
            "## Generation & revision sequence",
            "",
            "```mermaid",
            PIPELINE_SEQUENCE.strip(),
            "```",
            "",
            "## Artifact data dependencies",
            "",
            "```mermaid",
            DATA_FLOW_DIAGRAM.strip(),
            "```",
            "",
            "## Notes",
            "",
            "- **No direct agent-to-agent messaging.** Each specialist agent is stateless; "
            "`OrchestratorAgent` owns `WorkplanSession` and passes Pydantic models as arguments.",
            "- **LLM messages** are built per call via `BaseAgent.build_messages()` → "
            "`provider.call_structured()` (routed to OpenAI or Anthropic by model name).",
            "- **Web flow** splits parse and build: `parse_brief_only` may stop at "
            "`AWAITING_CONFIRMATION` before `generate_workplan_artifacts`.",
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
    parser.add_argument(
        "--mmd-only",
        action="store_true",
        help="Write only ARCHITECTURE.mmd (skip ARCHITECTURE.md)",
    )
    args = parser.parse_args()

    mermaid = build_mermaid_document()

    if args.stdout:
        print(mermaid, end="")
        return

    OUTPUT_MMD.write_text(mermaid, encoding="utf-8")
    print(f"Wrote {OUTPUT_MMD.relative_to(REPO_ROOT)}")

    if not args.mmd_only:
        OUTPUT_MD.write_text(build_markdown_wrapper(mermaid), encoding="utf-8")
        print(f"Wrote {OUTPUT_MD.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
